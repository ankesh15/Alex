import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import EmbeddingService
from app.config import settings


def _cosine_distance_python(v1: List[float], v2: List[float]) -> float:
    """Compute cosine distance in pure Python for non-pgvector environments (e.g. SQLite tests)."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 1.0
    cosine_sim = dot / (norm1 * norm2)
    return max(0.0, 1.0 - cosine_sim)


class VectorStoreService:
    """
    Vector retrieval service using pgvector (L2/Cosine similarity).
    Includes in-memory Python fallback for SQLite test suites.
    """

    @classmethod
    def search(
        cls,
        db: Session,
        query: str,
        document_id: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            return []

        limit_k = top_k if top_k is not None else settings.RAG_TOP_K
        query_vector = EmbeddingService.embed_text(query)

        dialect_name = db.bind.dialect.name if db.bind else "postgresql"

        if dialect_name == "postgresql":
            # PostgreSQL pgvector native similarity search
            distance_expr = DocumentChunk.embedding.l2_distance(query_vector)
            query_stmt = db.query(DocumentChunk, distance_expr.label("distance"))

            if document_id:
                query_stmt = query_stmt.filter(DocumentChunk.document_id == document_id)

            results = query_stmt.order_by(distance_expr.asc()).limit(limit_k).all()

            output = []
            for chunk, dist in results:
                output.append({
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "distance": float(dist) if dist is not None else 0.0
                })
            return output
        else:
            # Fallback for SQLite in-memory test environment
            query_stmt = db.query(DocumentChunk)
            if document_id:
                query_stmt = query_stmt.filter(DocumentChunk.document_id == document_id)
            all_chunks = query_stmt.all()

            scored_chunks = []
            for chunk in all_chunks:
                if chunk.embedding is not None:
                    # Convert embedding column to list if stored as list/array
                    emb_list = list(chunk.embedding) if not isinstance(chunk.embedding, list) else chunk.embedding
                    dist = _cosine_distance_python(query_vector, emb_list)
                    scored_chunks.append((chunk, dist))

            scored_chunks.sort(key=lambda x: x[1])
            top_results = scored_chunks[:limit_k]

            return [
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "distance": float(dist)
                }
                for chunk, dist in top_results
            ]
