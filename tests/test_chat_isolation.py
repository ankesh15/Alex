import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest
from langchain_core.messages import AIMessage

from app.core.db import Base
from app.api.main import app
from app.api.v1.endpoints.documents import get_db as doc_get_db
from app.api.v1.endpoints.chat import get_db as chat_get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import EmbeddingService
from app.config import settings

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[doc_get_db] = override_get_db
    app.dependency_overrides[chat_get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


client = TestClient(app)


def test_document_upload_and_listing_with_chat_id():
    # 1. Upload for chat-alpha
    res_alpha = client.post(
        "/api/v1/documents/upload",
        files={"file": ("alpha_notes.txt", b"Alpha research document content", "text/plain")},
        data={"chat_id": "chat-alpha"}
    )
    assert res_alpha.status_code == 201
    assert res_alpha.json()["chat_id"] == "chat-alpha"

    # 2. Upload for chat-beta
    res_beta = client.post(
        "/api/v1/documents/upload",
        files={"file": ("beta_notes.txt", b"Beta research document content", "text/plain")},
        data={"chat_id": "chat-beta"}
    )
    assert res_beta.status_code == 201
    assert res_beta.json()["chat_id"] == "chat-beta"

    # 3. List documents for chat-alpha
    list_alpha = client.get("/api/v1/documents?chat_id=chat-alpha")
    assert list_alpha.status_code == 200
    docs_alpha = list_alpha.json()["documents"]
    assert len(docs_alpha) == 1
    assert docs_alpha[0]["filename"] == "alpha_notes.txt"

    # 4. List documents for chat-beta
    list_beta = client.get("/api/v1/documents?chat_id=chat-beta")
    assert list_beta.status_code == 200
    docs_beta = list_beta.json()["documents"]
    assert len(docs_beta) == 1
    assert docs_beta[0]["filename"] == "beta_notes.txt"

    # 5. List for unknown chat
    list_gamma = client.get("/api/v1/documents?chat_id=chat-gamma")
    assert list_gamma.status_code == 200
    assert list_gamma.json()["total"] == 0


def test_rag_isolated_by_chat_id():
    db = TestingSessionLocal()
    try:
        # Chat 1 Document
        doc1 = Document(
            id="doc-chat-1",
            chat_id="chat-1",
            filename="quantum.txt",
            stored_filename="quantum.txt",
            file_type="txt",
            file_size=512,
            status="READY"
        )
        chunk1 = DocumentChunk(
            document_id="doc-chat-1",
            chunk_index=0,
            content="Quantum entanglement allows instantaneous quantum correlations.",
            embedding=EmbeddingService.embed_text("Quantum entanglement allows instantaneous quantum correlations.")
        )

        # Chat 2 Document
        doc2 = Document(
            id="doc-chat-2",
            chat_id="chat-2",
            filename="biology.txt",
            stored_filename="biology.txt",
            file_type="txt",
            file_size=512,
            status="READY"
        )
        chunk2 = DocumentChunk(
            document_id="doc-chat-2",
            chunk_index=0,
            content="Cellular mitosis is the process of cell division.",
            embedding=EmbeddingService.embed_text("Cellular mitosis is the process of cell division.")
        )

        db.add_all([doc1, chunk1, doc2, chunk2])
        db.commit()
    finally:
        db.close()

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="Quantum entanglement describes non-classical correlations between particles.",
        usage_metadata={"input_tokens": 30, "output_tokens": 15, "total_tokens": 45}
    )

    with patch("app.core.llm.get_llm", return_value=mock_llm):
        # Query Chat 1 with chat_id="chat-1"
        res1 = client.post(
            "/api/v1/chat",
            json={
                "question": "What is quantum entanglement?",
                "chat_id": "chat-1"
            }
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert len(data1["citations"]) == 1
        assert data1["citations"][0]["document_id"] == "doc-chat-1"

        # Query Chat 2 looking for quantum entanglement -> Should NOT find it in Chat 2!
        res2 = client.post(
            "/api/v1/chat",
            json={
                "question": "What is quantum entanglement?",
                "chat_id": "chat-2"
            }
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert "couldn't find enough relevant information" in data2["answer"]
        assert data2["citations"] == []


def test_delete_chat_documents():
    db = TestingSessionLocal()
    try:
        # Create temp file on disk to verify physical removal
        temp_file_name = "test_cleanup_file.txt"
        temp_path = os.path.join(settings.STORAGE_DIR, temp_file_name)
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        with open(temp_path, "w") as f:
            f.write("temporary file content")

        doc = Document(
            id="doc-cleanup-1",
            chat_id="chat-cleanup",
            filename="cleanup.txt",
            stored_filename=temp_file_name,
            file_type="txt",
            file_size=128,
            status="READY"
        )
        chunk = DocumentChunk(
            document_id="doc-cleanup-1",
            chunk_index=0,
            content="cleanup content",
            embedding=EmbeddingService.embed_text("cleanup content")
        )
        db.add_all([doc, chunk])
        db.commit()
    finally:
        db.close()

    assert os.path.exists(temp_path)

    # Call delete_chat_documents
    res = client.delete("/api/v1/documents/chat/chat-cleanup")
    assert res.status_code == 200
    assert res.json()["deleted_count"] == 1

    # Verify document and chunks removed from DB
    check_db = TestingSessionLocal()
    try:
        assert check_db.query(Document).filter(Document.id == "doc-cleanup-1").first() is None
        assert check_db.query(DocumentChunk).filter(DocumentChunk.document_id == "doc-cleanup-1").first() is None
    finally:
        check_db.close()

    # Verify physical file deleted from storage
    assert not os.path.exists(temp_path)
