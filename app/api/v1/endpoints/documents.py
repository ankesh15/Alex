import os
import uuid
import json
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.config import settings
from app.api.dependencies import get_db
from app.core.auth import AuthContext, get_current_user
from app.services.authorization import owned_conversation, owned_document, active_documents
from datetime import datetime, timezone
from app.models.document import Document
from app.models.conversation import Conversation
from app.models.document_chunk import DocumentChunk
from app.services.document_processor import DocumentProcessor
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.api.schemas import DocumentResponse, DocumentListResponse, DocumentDetailResponse

router = APIRouter()


def _safe_file_path(stored_filename: str) -> Optional[str]:
    """Ensures file paths cannot escape the designated storage directory."""
    if not stored_filename:
        return None
    storage_abs = os.path.abspath(settings.STORAGE_DIR)
    target_path = os.path.abspath(os.path.join(storage_abs, stored_filename))
    if os.path.commonpath([os.path.realpath(storage_abs), os.path.realpath(target_path)]) == os.path.realpath(storage_abs) and target_path != storage_abs:
        return target_path
    return None


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    chat_id: Optional[str] = Form(None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    db: Session = Depends(get_db),
    user: AuthContext = Depends(get_current_user)
):
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded or file filename is empty."
        )

    if chat_id:
        owned_conversation(db, chat_id, user.user_id, create=True, lock=True)

    # 1. Extension & File Type Validation
    original_filename = file.filename
    ext = os.path.splitext(original_filename)[1].lstrip(".").lower()
    if not ext or not DocumentProcessor.is_supported(ext):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '.{ext}'. Supported extensions are: PDF, DOCX, TXT."
        )

    # 2. File Size Validation
    contents = await file.read(settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1)
    file_size = len(contents)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        size_mb = file_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File size ({size_mb:.2f} MB) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    # 3. Create Storage & DB Record
    doc_id = str(uuid.uuid4())
    stored_filename = f"{doc_id}.{ext}"
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    file_path = _safe_file_path(stored_filename)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path configuration."
        )

    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        import logging
        logging.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file to storage."
        )

    doc_record = Document(
        id=doc_id,
        chat_id=chat_id,
        user_id=user.user_id,
        filename=original_filename,
        stored_filename=stored_filename,
        file_type=ext,
        file_size=file_size,
        status="PROCESSING"
    )
    db.add(doc_record)
    if chat_id:
        owned_conversation(db, chat_id, user.user_id, lock=True).updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(doc_record)

    # 4. Text Extraction, Chunking & Embedding Pipeline
    try:
        # Step A: Text Extraction
        extracted_pages = DocumentProcessor.extract_text(file_path, ext)

        # Step B: Text Chunking
        chunk_data_list = ChunkingService.split_pages(extracted_pages)

        # Step C: Batch Embedding Generation
        chunk_texts = [c["content"] for c in chunk_data_list]
        embeddings = EmbeddingService.embed_texts(chunk_texts) if chunk_texts else []
        # The conversation may have been deleted while CPU work ran in another worker.
        if chat_id:
            owned_conversation(db, chat_id, user.user_id, lock=True)
        doc_record = owned_document(db, doc_id, user.user_id)
        doc_record.extracted_text = json.dumps(extracted_pages)

        if chunk_data_list:

            # Step D: Delete existing chunks for doc_id if re-processing to prevent duplicates
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()

            # Step E: Create DocumentChunk records
            chunk_objects = []
            for item, emb in zip(chunk_data_list, embeddings):
                chunk_objects.append(
                    DocumentChunk(
                        document_id=doc_id,
                        chunk_index=item["chunk_index"],
                        content=item["content"],
                        page_number=item["page_number"],
                        embedding=emb
                    )
                )
            db.add_all(chunk_objects)

        doc_record.status = "READY"
        db.commit()
        db.refresh(doc_record)
    except Exception:
        db.rollback()
        if chat_id:
            owned_conversation(db, chat_id, user.user_id, lock=True)
        doc_record = owned_document(db, doc_id, user.user_id)
        doc_record.status = "FAILED"
        doc_record.error_message = "Document processing failed. Please verify the file and try again."
        db.commit()
        db.refresh(doc_record)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document pipeline processing failed. Please verify the file and try again."
        )

    return doc_record


@router.get("", response_model=DocumentListResponse)
def list_documents(
    chat_id: Optional[str] = Query(None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    db: Session = Depends(get_db),
    user: AuthContext = Depends(get_current_user)
):
    query = db.query(Document).filter(Document.user_id == user.user_id, *active_documents(user.user_id))
    if chat_id:
        existing = db.get(Conversation, chat_id)
        if existing is not None:
            owned_conversation(db, chat_id, user.user_id)
        query = query.filter(Document.chat_id == chat_id)
    documents = query.order_by(Document.created_at.desc()).all()
    return DocumentListResponse(
        documents=documents,
        total=len(documents)
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(document_id: str, db: Session = Depends(get_db),
                 user: AuthContext = Depends(get_current_user)):
    doc = owned_document(db, document_id, user.user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    page_count = 0
    if doc.extracted_text:
        try:
            pages = json.loads(doc.extracted_text)
            page_count = len(pages)
        except Exception:
            page_count = 0

    return DocumentDetailResponse(
        id=doc.id,
        chat_id=doc.chat_id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status,
        error_message=doc.error_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        page_count=page_count
    )


@router.delete("/chat/{chat_id}")
def delete_chat_documents(chat_id: str, db: Session = Depends(get_db),
                          user: AuthContext = Depends(get_current_user)):
    """
    Deletes all temporary documents, physical files, chunks, and embeddings
    associated with a specific chat session.
    """
    existing = db.get(Conversation, chat_id)
    if existing is not None:
        owned_conversation(db, chat_id, user.user_id)
    docs = db.query(Document).filter(Document.chat_id == chat_id, Document.user_id == user.user_id).all()
    deleted_count = 0
    for doc in docs:
        file_path = _safe_file_path(doc.stored_filename)
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        db.delete(doc)
        deleted_count += 1
    db.commit()
    return {
        "message": f"Successfully deleted {deleted_count} documents for chat '{chat_id}'.",
        "deleted_count": deleted_count
    }


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db),
                    user: AuthContext = Depends(get_current_user)):
    doc = owned_document(db, document_id, user.user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    # 1. Remove Physical File
    file_path = _safe_file_path(doc.stored_filename)
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass  # Handle missing/locked files gracefully

    # 2. Delete Database Record (Cascades to DocumentChunk)
    db.delete(doc)
    db.commit()

    return {"message": "Document deleted successfully", "id": document_id}
