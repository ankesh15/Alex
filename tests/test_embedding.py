from app.services.embedding_service import EmbeddingService
from app.config import settings


def test_embedding_model_dimension():
    vec = EmbeddingService.embed_text("Alex vector search test")
    assert isinstance(vec, list)
    assert len(vec) == settings.EMBEDDING_DIMENSION
    assert len(vec) == 384


def test_embedding_batch_generation():
    texts = [
        "First document paragraph about astrophysics.",
        "Second paragraph discussing machine learning embeddings.",
        "Third statement regarding database indexing."
    ]
    embeddings = EmbeddingService.embed_texts(texts)
    assert len(embeddings) == 3
    for emb in embeddings:
        assert isinstance(emb, list)
        assert len(emb) == 384


def test_embedding_empty_text():
    vec = EmbeddingService.embed_text("")
    assert len(vec) == 384
    assert all(val == 0.0 for val in vec)
