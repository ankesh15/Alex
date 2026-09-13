import uuid
import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.audit_log import AgentAuditLog
from app.services.embedding_service import EmbeddingService
from app.services.rag_service import RAGService


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_build_context_formatting():
    chunks = [
        {
            "filename": "quantum_computing.pdf",
            "page_number": 3,
            "content": "Qubits exhibit superposition and entanglement."
        },
        {
            "filename": "notes.txt",
            "page_number": None,
            "content": "Quantum decoherence occurs due to thermal noise."
        }
    ]
    context = RAGService.build_context(chunks)
    assert "SOURCE 1" in context
    assert "Document: quantum_computing.pdf" in context
    assert "Page: 3" in context
    assert "Qubits exhibit superposition and entanglement." in context

    assert "SOURCE 2" in context
    assert "Document: notes.txt" in context
    assert "Page: N/A" in context
    assert "Quantum decoherence occurs due to thermal noise." in context


def test_build_context_empty():
    assert RAGService.build_context([]) == ""


def test_build_prompt_rules():
    prompt = RAGService.build_prompt(
        question="What is superposition?",
        context_str="Sample context content"
    )
    assert "You are Alex" in prompt
    assert "RULES:" in prompt
    assert "Do NOT invent facts" in prompt
    assert "RETRIEVED CONTEXT:" in prompt
    assert "Sample context content" in prompt
    assert "USER QUESTION:" in prompt
    assert "What is superposition?" in prompt


def test_retrieve_context_with_threshold_filtering(db_session):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="physics.pdf",
        stored_filename=f"{doc_id}.pdf",
        file_type="pdf",
        file_size=2048,
        status="READY"
    )
    db_session.add(doc)

    relevant_text = "General relativity describes gravitation as a geometric property of spacetime."
    irrelevant_text = "The recipe calls for two tablespoons of olive oil and garlic."

    c1 = DocumentChunk(
        document_id=doc_id,
        chunk_index=0,
        content=relevant_text,
        page_number=1,
        embedding=EmbeddingService.embed_text(relevant_text)
    )
    c2 = DocumentChunk(
        document_id=doc_id,
        chunk_index=1,
        content=irrelevant_text,
        page_number=2,
        embedding=EmbeddingService.embed_text(irrelevant_text)
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    # Query specifically about gravity and spacetime
    results = RAGService.retrieve_context(
        db=db_session,
        question="gravitation and spacetime curvature",
        top_k=5,
        threshold=0.65
    )

    assert len(results) >= 1
    # Relevant physics chunk should be retrieved
    assert any("General relativity" in r["content"] for r in results)
    # The culinary chunk should either not be present or have higher distance
    for r in results:
        assert r["distance"] <= 0.65


def test_generate_answer_mocked_llm():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="Superposition allows quantum systems to exist in multiple states simultaneously.",
        usage_metadata={"input_tokens": 50, "output_tokens": 15, "total_tokens": 65}
    )

    prompt = "Test prompt"
    answer, token_usage = RAGService.generate_answer(prompt, llm=mock_llm)

    assert "Superposition" in answer
    assert token_usage["prompt_tokens"] == 50
    assert token_usage["completion_tokens"] == 15
    assert token_usage["total_tokens"] == 65
    mock_llm.invoke.assert_called_once_with(prompt)


def test_build_citations():
    chunks = [
        {
            "chunk_id": "c-123",
            "document_id": "d-456",
            "filename": "ai_report.pdf",
            "page_number": 5,
            "similarity_score": 0.88,
            "distance": 0.12
        }
    ]
    citations = RAGService.build_citations(chunks)
    assert len(citations) == 1
    assert citations[0]["chunk_id"] == "c-123"
    assert citations[0]["document_id"] == "d-456"
    assert citations[0]["filename"] == "ai_report.pdf"
    assert citations[0]["page_number"] == 5
    assert citations[0]["relevance_score"] == 0.88


def test_log_audit_records_successfully(db_session):
    task_id = "test-task-123"
    RAGService.log_audit(
        db=db_session,
        task_id=task_id,
        question="What is Alex?",
        answer="Alex is an AI research assistant.",
        token_usage={"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
        status="SUCCESS"
    )

    log = db_session.query(AgentAuditLog).filter(AgentAuditLog.task_id == task_id).first()
    assert log is not None
    assert log.module_name == "rag"
    assert log.status == "SUCCESS"
    assert log.prompt_tokens == 20
    assert log.completion_tokens == 10
    assert log.total_tokens == 30
    assert "Alex is an AI" in log.output_result
