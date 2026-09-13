import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import EmbeddingService
from app.config import settings


def _cosine_distance_python(v1: List[float], v2: List[float]) -> float:
    """Compute cosine distance in pure Python for non-pgvector environments (e.g. SQLite tests).
    0.0 = identical vectors, 1.0 = orthogonal, 2.0 = opposite.
    """
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 1.0
    cosine_sim = dot / (norm1 * norm2)
    # Cosine distance = 1 - cosine similarity
    return max(0.0, 1.0 - cosine_sim)


class VectorStoreService:
    """
    Vector retrieval service using pgvector cosine distance.
    Includes in-memory Python fallback for SQLite test suites.
    Joins DocumentChunk with Document to return full citation metadata.
    Only retrieves chunks from READY documents.
    """

    @classmethod
    def search(
        cls,
        db: Session,
        query: str,
        document_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            return []

        limit_k = top_k if top_k is not None else settings.RAG_TOP_K
        query_vector = EmbeddingService.embed_text(query)

        dialect_name = db.bind.dialect.name if db.bind else "postgresql"

        if dialect_name == "postgresql":
            # PostgreSQL pgvector native cosine distance search
            distance_expr = DocumentChunk.embedding.cosine_distance(query_vector)
            query_stmt = (
                db.query(DocumentChunk, Document, distance_expr.label("distance"))
                .join(Document, DocumentChunk.document_id == Document.id)
                .filter(Document.status == "READY")
            )

            if chat_id:
                query_stmt = query_stmt.filter(Document.chat_id == chat_id)

            if document_id:
                query_stmt = query_stmt.filter(DocumentChunk.document_id == document_id)

            results = query_stmt.order_by(distance_expr.asc()).limit(limit_k).all()

            output = []
            for chunk, doc, dist in results:
                d_val = float(dist) if dist is not None else 0.0
                sim_score = max(0.0, round(1.0 - d_val, 4))
                output.append({
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "filename": doc.filename,
                    "file_type": doc.file_type,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "distance": round(d_val, 4),
                    "similarity_score": sim_score
                })
            return output
        else:
            # Fallback for SQLite in-memory test environment
            query_stmt = (
                db.query(DocumentChunk, Document)
                .join(Document, DocumentChunk.document_id == Document.id)
                .filter(Document.status == "READY")
            )
            if chat_id:
                query_stmt = query_stmt.filter(Document.chat_id == chat_id)
            if document_id:
                query_stmt = query_stmt.filter(DocumentChunk.document_id == document_id)
            all_records = query_stmt.all()

            scored_chunks = []
            for chunk, doc in all_records:
                if chunk.embedding is not None:
                    emb_list = list(chunk.embedding) if not isinstance(chunk.embedding, list) else chunk.embedding
                    dist = _cosine_distance_python(query_vector, emb_list)
                    scored_chunks.append((chunk, doc, dist))

            scored_chunks.sort(key=lambda x: x[2])
            top_results = scored_chunks[:limit_k]

            return [
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "filename": doc.filename,
                    "file_type": doc.file_type,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "distance": round(float(dist), 4),
                    "similarity_score": max(0.0, round(1.0 - float(dist), 4))
                }
                for chunk, doc, dist in top_results
            ]
