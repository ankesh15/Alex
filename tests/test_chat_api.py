from unittest.mock import patch, MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.core.db import Base
from app.api.main import app
from app.api.v1.endpoints.chat import get_db as chat_get_db
from app.api.v1.endpoints.documents import get_db as doc_get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.audit_log import AgentAuditLog
from app.services.embedding_service import EmbeddingService
from app.services.rag_service import INSUFFICIENT_CONTEXT_MESSAGE


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

    app.dependency_overrides[chat_get_db] = override_get_db
    app.dependency_overrides[doc_get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


client = TestClient(app)


def test_chat_success_with_citations():
    db = TestingSessionLocal()
    try:
        doc = Document(
            id="doc-research-1",
            filename="transformer_paper.pdf",
            stored_filename="doc-research-1.pdf",
            file_type="pdf",
            file_size=1024,
            status="READY"
        )
        content = "The Transformer architecture relies entirely on self-attention mechanisms without recurrence."
        chunk = DocumentChunk(
            document_id="doc-research-1",
            chunk_index=0,
            content=content,
            page_number=1,
            embedding=EmbeddingService.embed_text(content)
        )
        db.add_all([doc, chunk])
        db.commit()
    finally:
        db.close()

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="The Transformer model is based entirely on self-attention mechanisms without recurrent networks.",
        usage_metadata={"input_tokens": 45, "output_tokens": 16, "total_tokens": 61}
    )

    with patch("app.core.llm.get_llm", return_value=mock_llm):
        response = client.post(
            "/api/v1/chat",
            json={"question": "What is the Transformer architecture based on?"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "Transformer" in data["answer"]
    assert "task_id" in data
    assert len(data["citations"]) == 1

    citation = data["citations"][0]
    assert citation["document_id"] == "doc-research-1"
    assert citation["filename"] == "transformer_paper.pdf"
    assert citation["page_number"] == 1
    assert citation["relevance_score"] > 0.0

    # Verify AgentAuditLog was persisted in DB
    verify_db = TestingSessionLocal()
    try:
        audit = verify_db.query(AgentAuditLog).filter(AgentAuditLog.task_id == data["task_id"]).first()
        assert audit is not None
        assert audit.module_name == "rag"
        assert audit.status == "SUCCESS"
        assert audit.prompt_tokens == 45
        assert audit.completion_tokens == 16
        assert audit.total_tokens == 61
    finally:
        verify_db.close()


def test_chat_insufficient_context():
    # Empty DB - no documents
    mock_llm = MagicMock()
    with patch("app.core.llm.get_llm", return_value=mock_llm):
        response = client.post(
            "/api/v1/chat",
            json={"question": "What are the latest advances in fusion energy?"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == INSUFFICIENT_CONTEXT_MESSAGE
    assert data["citations"] == []
    # LLM should never be invoked when no context is found
    mock_llm.invoke.assert_not_called()


def test_chat_empty_question_validation():
    response = client.post("/api/v1/chat", json={"question": "   "})
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]


def test_chat_document_id_filter():
    db = TestingSessionLocal()
    try:
        doc_a = Document(
            id="doc-a",
            filename="document_a.pdf",
            stored_filename="doc-a.pdf",
            file_type="pdf",
            file_size=1024,
            status="READY"
        )
        chunk_a = DocumentChunk(
            document_id="doc-a",
            chunk_index=0,
            content="Document A describes project management best practices and agile sprints.",
            page_number=3,
            embedding=EmbeddingService.embed_text("Document A describes project management best practices and agile sprints.")
        )

        doc_b = Document(
            id="doc-b",
            filename="document_b.pdf",
            stored_filename="doc-b.pdf",
            file_type="pdf",
            file_size=1024,
            status="READY"
        )
        chunk_b = DocumentChunk(
            document_id="doc-b",
            chunk_index=0,
            content="Document B provides guidance on database schema design and normalization.",
            page_number=7,
            embedding=EmbeddingService.embed_text("Document B provides guidance on database schema design and normalization.")
        )

        db.add_all([doc_a, chunk_a, doc_b, chunk_b])
        db.commit()
    finally:
        db.close()

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="Document A emphasizes agile methodology and sprints.",
        usage_metadata={"input_tokens": 35, "output_tokens": 10, "total_tokens": 45}
    )

    with patch("app.core.llm.get_llm", return_value=mock_llm):
        # Target explicitly doc-a
        response = client.post(
            "/api/v1/chat",
            json={
                "question": "What does this document say about project management?",
                "document_id": "doc-a"
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["citations"]) == 1
    assert data["citations"][0]["document_id"] == "doc-a"
    assert data["citations"][0]["filename"] == "document_a.pdf"


def test_chat_gemini_api_failure_handled_gracefully():
    db = TestingSessionLocal()
    try:
        doc = Document(
            id="doc-fail",
            filename="error_doc.pdf",
            stored_filename="error_doc.pdf",
            file_type="pdf",
            file_size=1024,
            status="READY"
        )
        chunk = DocumentChunk(
            document_id="doc-fail",
            chunk_index=0,
            content="Some valid content to ensure context retrieval succeeds.",
            page_number=1,
            embedding=EmbeddingService.embed_text("Some valid content to ensure context retrieval succeeds.")
        )
        db.add_all([doc, chunk])
        db.commit()
    finally:
        db.close()

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("API_KEY_INVALID: API key not valid. Please pass a valid API key.")

    with patch("app.core.llm.get_llm", return_value=mock_llm):
        response = client.post(
            "/api/v1/chat",
            json={
                "question": "Tell me about this valid content"
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert "Alex couldn't generate an answer right now" in data["answer"]
    assert "Gemini API key" in data["answer"]
    assert data["citations"] == []

