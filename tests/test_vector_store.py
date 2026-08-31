import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.db import Base
from app.models.document import Document
from app.models.document_chunk import DocumentChunk  # noqa: F401
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService

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


def test_document_chunk_relationship_and_cascading_delete(db_session):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="cascading_test.pdf",
        stored_filename=f"{doc_id}.pdf",
        file_type="pdf",
        file_size=1024,
        status="READY"
    )
    db_session.add(doc)

    emb = EmbeddingService.embed_text("Sample chunk text")
    chunk1 = DocumentChunk(
        document_id=doc_id,
        chunk_index=0,
        content="Sample chunk text",
        page_number=1,
        embedding=emb
    )
    db_session.add(chunk1)
    db_session.commit()

    # Verify query
    saved_chunks = db_session.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
    assert len(saved_chunks) == 1
    assert len(doc.chunks) == 1

    # Delete Document and verify chunks are cascade deleted
    db_session.delete(doc)
    db_session.commit()

    remaining_chunks = db_session.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
    assert len(remaining_chunks) == 0


def test_vector_search_similarity(db_session):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="search_test.txt",
        stored_filename=f"{doc_id}.txt",
        file_type="txt",
        file_size=2048,
        status="READY"
    )
    db_session.add(doc)

    texts = [
        "Astrophysics is the branch of astronomy that employs principles of physics.",
        "Deep learning models utilize neural networks with multiple layers.",
        "PostgreSQL is an open-source relational database management system."
    ]

    embeddings = EmbeddingService.embed_texts(texts)
    for idx, (t, emb) in enumerate(zip(texts, embeddings)):
        c = DocumentChunk(
            document_id=doc_id,
            chunk_index=idx,
            content=t,
            page_number=None,
            embedding=emb
        )
        db_session.add(c)
    db_session.commit()

    # Search query about astronomy
    results = VectorStoreService.search(db_session, query="physics and stars", top_k=2)
    assert len(results) == 2
    assert "Astrophysics" in results[0]["content"]

    # Search query about database
    db_results = VectorStoreService.search(db_session, query="relational database query", top_k=1)
    assert len(db_results) == 1
    assert "PostgreSQL" in db_results[0]["content"]
