from typing import List
from fastembed import TextEmbedding
from app.config import settings


class EmbeddingService:
    """
    Embedding generation service using FastEmbed.
    Uses reusable singleton model instance (CPU optimized via ONNX).
    """

    _model: TextEmbedding | None = None

    @classmethod
    def get_model(cls) -> TextEmbedding:
        if cls._model is None:
            cls._model = TextEmbedding(model_name=settings.EMBEDDING_MODEL)
        return cls._model

    @classmethod
    def embed_text(cls, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * settings.EMBEDDING_DIMENSION

        model = cls.get_model()
        embeddings = list(model.embed([text]))
        return embeddings[0].tolist()

    @classmethod
    def embed_texts(cls, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # Filter out empty or whitespace-only strings for embedding call
        non_empty_texts = [t if t and t.strip() else " " for t in texts]
        model = cls.get_model()
        embeddings = list(model.embed(non_empty_texts))
        return [e.tolist() for e in embeddings]
