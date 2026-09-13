import json
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.config import settings
from app.core import llm as llm_core
from app.models.audit_log import AgentAuditLog
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

INSUFFICIENT_CONTEXT_MESSAGE = (
    "I couldn't find enough relevant information in the uploaded documents to answer this question."
)


class RAGService:
    """
    Core RAG coordination service for Alex.
    Coordinates vector retrieval, relevance thresholding, prompt construction,
    grounded LLM synthesis, and structured citation building.
    """

    @classmethod
    def retrieve_context(
        cls,
        db: Session,
        question: str,
        document_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Embeds the question and retrieves chunks filtered by cosine distance threshold.
        Cosine distance: 0.0 is identical. Distance <= threshold means relevant.
        """
        if not question or not question.strip():
            return []

        limit_k = top_k if top_k is not None else settings.RAG_TOP_K
        dist_threshold = threshold if threshold is not None else settings.RAG_SIMILARITY_THRESHOLD

        raw_chunks = VectorStoreService.search(
            db=db,
            query=question,
            document_id=document_id,
            chat_id=chat_id,
            top_k=limit_k
        )

        # Filter out chunks that exceed the cosine distance threshold (less relevant)
        relevant_chunks = [c for c in raw_chunks if c["distance"] <= dist_threshold]
        return relevant_chunks

    @classmethod
    def build_context(cls, chunks: List[Dict[str, Any]]) -> str:
        """
        Builds human-readable structured context for Gemini from retrieved chunks.
        """
        if not chunks:
            return ""

        context_blocks = []
        for idx, chunk in enumerate(chunks, 1):
            page_info = f"Page: {chunk['page_number']}" if chunk.get("page_number") is not None else "Page: N/A"
            block = (
                f"SOURCE {idx}\n"
                f"Document: {chunk.get('filename', 'Unknown')}\n"
                f"{page_info}\n\n"
                f"Content:\n{chunk.get('content', '').strip()}"
            )
            context_blocks.append(block)

        return "\n\n---\n\n".join(context_blocks)

    @classmethod
    def build_prompt(cls, question: str, context_str: str) -> str:
        """
        Builds the grounded RAG prompt strictly preventing hallucinations.
        """
        return (
            "You are Alex, an AI knowledge and research assistant.\n"
            "Your job is to answer the user's question using ONLY the retrieved document context below.\n\n"
            "RULES:\n"
            "1. Answer using ONLY the supplied context below. Do NOT invent facts or extrapolate beyond what is stated.\n"
            f'2. If the context does not contain enough information to answer the question, clearly state: "{INSUFFICIENT_CONTEXT_MESSAGE}"\n'
            "3. Do NOT hallucinate. Do NOT mention external information not supported by the context.\n"
            "4. Cite the source document and page number supporting important statements where available.\n"
            "5. Do not fabricate page numbers or document names.\n"
            "6. Keep the answer clear, objective, and well-structured.\n\n"
            "RETRIEVED CONTEXT:\n"
            f"{context_str}\n\n"
            "USER QUESTION:\n"
            f"{question.strip()}"
        )

    @classmethod
    def generate_answer(cls, prompt: str, llm=None) -> Tuple[str, Dict[str, int]]:
        """
        Invokes Gemini with the prompt and extracts the clean text and token usage.
        """
        chat_llm = llm if llm is not None else llm_core.get_llm(temperature=0.0)
        try:
            response = chat_llm.invoke(prompt)
            return llm_core.parse_llm_response(response)
        except Exception as e:
            err_str = str(e)
            if "API_KEY_INVALID" in err_str or "API key not valid" in err_str or "INVALID_ARGUMENT" in err_str:
                error_answer = (
                    "Alex couldn't generate an answer right now. "
                    "Please check the Gemini API key configuration and try again."
                )
            elif "quota" in err_str.lower() or "resource_exhausted" in err_str.lower():
                error_answer = (
                    "Alex couldn't generate an answer right now due to Gemini API quota limits. "
                    "Please try again in a few moments."
                )
            else:
                error_answer = (
                    "Alex couldn't generate an answer right now. "
                    "Please check the Gemini configuration and try again."
                )
            return error_answer, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    @classmethod
    def build_citations(cls, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Constructs clean citation objects from the retrieved chunks.
        """
        citations = []
        for chunk in chunks:
            sim_score = chunk.get("similarity_score")
            if sim_score is None:
                dist = chunk.get("distance", 0.0)
                sim_score = max(0.0, round(1.0 - dist, 4))

            citations.append({
                "document_id": chunk["document_id"],
                "filename": chunk["filename"],
                "page_number": chunk.get("page_number"),
                "chunk_id": chunk["chunk_id"],
                "relevance_score": float(sim_score)
            })
        return citations

    @classmethod
    def log_audit(
        cls,
        db: Session,
        task_id: str,
        question: str,
        answer: str,
        token_usage: Optional[Dict[str, int]] = None,
        status: str = "COMPLETED"
    ) -> None:
        """
        Safely records query execution and token metrics to AgentAuditLog.
        """
        try:
            tokens = token_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            audit_record = AgentAuditLog(
                task_id=task_id,
                module_name="rag",
                status=status,
                input_data=json.dumps({"question": question}),
                output_result=json.dumps({"answer": answer[:500]}),
                prompt_tokens=tokens.get("prompt_tokens", 0),
                completion_tokens=tokens.get("completion_tokens", 0),
                total_tokens=tokens.get("total_tokens", 0)
            )
            db.add(audit_record)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Failed to record AgentAuditLog for task {task_id}: {e}")

    @classmethod
    def run_rag(
        cls,
        db: Session,
        question: str,
        document_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
        llm=None
    ) -> Dict[str, Any]:
        """
        Executes the RAG pipeline via LangGraph orchestration and logs audit records.
        """
        from app.agents.rag_agent import create_rag_graph

        task_id = str(uuid.uuid4())
        rag_graph = create_rag_graph(db=db, llm=llm)

        initial_state = {
            "question": question,
            "document_id": document_id,
            "chat_id": chat_id,
            "top_k": top_k or settings.RAG_TOP_K,
            "threshold": threshold if threshold is not None else settings.RAG_SIMILARITY_THRESHOLD,
            "chunks": [],
            "context_str": "",
            "answer": "",
            "citations": [],
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "status": "INITIALIZED",
            "error": None
        }

        final_state = rag_graph.invoke(initial_state)

        # Record audit log
        cls.log_audit(
            db=db,
            task_id=task_id,
            question=question,
            answer=final_state["answer"],
            token_usage=final_state["token_usage"],
            status=final_state["status"]
        )

        return {
            "answer": final_state["answer"],
            "citations": final_state["citations"],
            "task_id": task_id,
            "token_usage": final_state["token_usage"]
        }
