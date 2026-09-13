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
from app.services.embedding_service import EmbeddingService
from app.services.rag_service import INSUFFICIENT_CONTEXT_MESSAGE
from app.agents.rag_agent import create_rag_graph


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


def test_rag_agent_successful_workflow(db_session):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="distributed_systems.pdf",
        stored_filename=f"{doc_id}.pdf",
        file_type="pdf",
        file_size=1024,
        status="READY"
    )
    db_session.add(doc)

    content = "Raft is a consensus algorithm designed as an alternative to Paxos."
    chunk = DocumentChunk(
        document_id=doc_id,
        chunk_index=0,
        content=content,
        page_number=2,
        embedding=EmbeddingService.embed_text(content)
    )
    db_session.add(chunk)
    db_session.commit()

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="Raft is an understandable consensus algorithm alternative to Paxos.",
        usage_metadata={"input_tokens": 40, "output_tokens": 12, "total_tokens": 52}
    )

    graph = create_rag_graph(db=db_session, llm=mock_llm)
    state = {
        "question": "What is Raft consensus algorithm?",
        "document_id": None,
        "top_k": 5,
        "threshold": 0.65,
        "chunks": [],
        "context_str": "",
        "answer": "",
        "citations": [],
        "token_usage": {},
        "status": "START",
        "error": None
    }

    result = graph.invoke(state)

    assert result["status"] == "SUCCESS"
    assert "Raft is an understandable consensus" in result["answer"]
    assert len(result["citations"]) == 1
    assert result["citations"][0]["filename"] == "distributed_systems.pdf"
    assert result["citations"][0]["page_number"] == 2
    assert result["token_usage"]["total_tokens"] == 52
    mock_llm.invoke.assert_called_once()


def test_rag_agent_insufficient_context_workflow(db_session):
    # Empty DB - no documents present
    mock_llm = MagicMock()
    graph = create_rag_graph(db=db_session, llm=mock_llm)

    state = {
        "question": "Explain quantum chromodynamics.",
        "document_id": None,
        "top_k": 5,
        "threshold": 0.65,
        "chunks": [],
        "context_str": "",
        "answer": "",
        "citations": [],
        "token_usage": {},
        "status": "START",
        "error": None
    }

    result = graph.invoke(state)

    assert result["status"] == "NO_CONTEXT"
    assert result["answer"] == INSUFFICIENT_CONTEXT_MESSAGE
    assert result["citations"] == []
    assert result["token_usage"]["total_tokens"] == 0
    # Gemini must NOT be called when context is insufficient
    mock_llm.invoke.assert_not_called()


def test_rag_agent_document_specific_filter(db_session):
    # Doc 1: Biology
    doc1_id = str(uuid.uuid4())
    doc1 = Document(id=doc1_id, filename="biology.txt", stored_filename=f"{doc1_id}.txt", file_type="txt", file_size=500, status="READY")
    c1 = DocumentChunk(
        document_id=doc1_id, chunk_index=0, content="Mitochondria are the powerhouse of the cell.",
        page_number=None, embedding=EmbeddingService.embed_text("Mitochondria are the powerhouse of the cell.")
    )

    # Doc 2: History
    doc2_id = str(uuid.uuid4())
    doc2 = Document(id=doc2_id, filename="history.txt", stored_filename=f"{doc2_id}.txt", file_type="txt", file_size=500, status="READY")
    c2 = DocumentChunk(
        document_id=doc2_id, chunk_index=0, content="The Industrial Revolution began in Great Britain.",
        page_number=None, embedding=EmbeddingService.embed_text("The Industrial Revolution began in Great Britain.")
    )

    db_session.add_all([doc1, doc2, c1, c2])
    db_session.commit()

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="Mitochondria produce energy via ATP synthesis.",
        usage_metadata={"input_tokens": 30, "output_tokens": 10, "total_tokens": 40}
    )

    graph = create_rag_graph(db=db_session, llm=mock_llm)

    # Filter to only doc1
    state = {
        "question": "What is the cell powerhouse?",
        "document_id": doc1_id,
        "top_k": 3,
        "threshold": 0.65,
        "chunks": [],
        "context_str": "",
        "answer": "",
        "citations": [],
        "token_usage": {},
        "status": "START",
        "error": None
    }

    result = graph.invoke(state)
    assert result["status"] == "SUCCESS"
    assert len(result["citations"]) == 1
    assert result["citations"][0]["document_id"] == doc1_id
    assert result["citations"][0]["filename"] == "biology.txt"
