import os
import uuid
import json
from typing import Generator
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.config import settings
from app.core.db import SessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.document_processor import DocumentProcessor
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.api.schemas import DocumentResponse, DocumentListResponse, DocumentDetailResponse

router = APIRouter()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded or file filename is empty."
        )

    # 1. Extension & File Type Validation
    original_filename = file.filename
    ext = os.path.splitext(original_filename)[1].lstrip(".").lower()
    if not ext or not DocumentProcessor.is_supported(ext):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '.{ext}'. Supported extensions are: PDF, DOCX, TXT."
        )

    # 2. File Size Validation
    contents = await file.read()
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
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({size_mb:.2f} MB) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    # 3. Create Storage & DB Record
    doc_id = str(uuid.uuid4())
    stored_filename = f"{doc_id}.{ext}"
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    file_path = os.path.join(settings.STORAGE_DIR, stored_filename)

    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file to storage: {str(e)}"
        )

    doc_record = Document(
        id=doc_id,
        filename=original_filename,
        stored_filename=stored_filename,
        file_type=ext,
        file_size=file_size,
        status="PROCESSING"
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    # 4. Text Extraction, Chunking & Embedding Pipeline
    try:
        # Step A: Text Extraction
        extracted_pages = DocumentProcessor.extract_text(file_path, ext)
        doc_record.extracted_text = json.dumps(extracted_pages)

        # Step B: Text Chunking
        chunk_data_list = ChunkingService.split_pages(extracted_pages)

        # Step C: Batch Embedding Generation
        if chunk_data_list:
            chunk_texts = [c["content"] for c in chunk_data_list]
            embeddings = EmbeddingService.embed_texts(chunk_texts)

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
    except Exception as e:
        doc_record.status = "FAILED"
        doc_record.error_message = str(e)
        db.commit()
        db.refresh(doc_record)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document pipeline processing failed: {str(e)}"
        )

    return doc_record


@router.get("", response_model=DocumentListResponse)
def list_documents(db: Session = Depends(get_db)):
    documents = db.query(Document).order_by(Document.created_at.desc()).all()
    return DocumentListResponse(
        documents=documents,
        total=len(documents)
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
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
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status,
        error_message=doc.error_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        page_count=page_count
    )


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    # 1. Remove Physical File
    file_path = os.path.join(settings.STORAGE_DIR, doc.stored_filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass  # Handle missing/locked files gracefully

    # 2. Delete Database Record (Cascades to DocumentChunk)
    db.delete(doc)
    db.commit()

    return {"message": "Document deleted successfully", "id": document_id}
