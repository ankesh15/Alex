from typing import TypedDict, List, Dict, Any, Optional
from sqlalchemy.orm import Session
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from app.services.rag_service import RAGService, INSUFFICIENT_CONTEXT_MESSAGE, HISTORY_RULES


class RAGState(TypedDict):
    question: str
    history: List[BaseMessage]
    retrieval_question: str
    rewrite_token_usage: Dict[str, int]
    document_id: Optional[str]
    chat_id: Optional[str]
    top_k: int
    threshold: float
    chunks: List[Dict[str, Any]]
    context_str: str
    answer: str
    citations: List[Dict[str, Any]]
    token_usage: Dict[str, int]
    status: str
    error: Optional[str]


def create_rag_graph(db: Session, llm=None, *, user_id: str):
    """
    Creates and compiles a simple, maintainable LangGraph workflow for Document RAG:

    START
      ↓
    contextualize_question → retrieve_context
      ↓
    check_context
      ├── no_context  → insufficient_context → END
      └── has_context → generate_answer → build_citations → END
    """

    def contextualize_question_node(state: RAGState) -> Dict[str, Any]:
        question, usage = RAGService.contextualize_question(state["question"], state.get("history", []), llm=llm)
        return {"retrieval_question": question, "rewrite_token_usage": usage}

    def retrieve_context_node(state: RAGState) -> Dict[str, Any]:
        chunks = RAGService.retrieve_context(
            db=db,
            question=state.get("retrieval_question", state["question"]),
            document_id=state.get("document_id"),
            chat_id=state.get("chat_id"),
            top_k=state.get("top_k"),
            threshold=state.get("threshold"),
            user_id=user_id
        )
        # Retrieval returns plain dictionaries; release its connection before Gemini.
        db.commit()
        return {"chunks": chunks}

    def check_context_condition(state: RAGState) -> str:
        chunks = state.get("chunks", [])
        if not chunks:
            return "no_context"
        return "has_context"

    def insufficient_context_node(state: RAGState) -> Dict[str, Any]:
        return {
            "answer": INSUFFICIENT_CONTEXT_MESSAGE,
            "citations": [],
            "status": "NO_CONTEXT",
            "token_usage": state.get("rewrite_token_usage", {})
        }

    def generate_answer_node(state: RAGState) -> Dict[str, Any]:
        chunks = state["chunks"]
        context_str = RAGService.build_context(chunks)
        prompt = RAGService.build_prompt(state["question"], context_str)
        if state.get("history"):
            prompt = [
                SystemMessage(content=HISTORY_RULES),
                *state["history"],
                HumanMessage(content=prompt),
            ]
        answer, token_usage = RAGService.generate_answer(prompt, llm=llm)
        rewrite_usage = state.get("rewrite_token_usage", {})
        token_usage = {key: token_usage.get(key, 0) + rewrite_usage.get(key, 0)
                       for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
        is_err = RAGService.is_generation_error(answer)
        return {
            "context_str": context_str,
            "answer": answer,
            "token_usage": token_usage,
            "status": "ERROR" if is_err else "SUCCESS"
        }

    def build_citations_node(state: RAGState) -> Dict[str, Any]:
        if state.get("status") == "ERROR":
            return {"citations": []}
        citations = RAGService.build_citations(state["chunks"])
        return {"citations": citations}

    workflow = StateGraph(RAGState)

    # Add workflow nodes
    workflow.add_node("contextualize_question", contextualize_question_node)
    workflow.add_node("retrieve_context", retrieve_context_node)
    workflow.add_node("insufficient_context", insufficient_context_node)
    workflow.add_node("generate_answer", generate_answer_node)
    workflow.add_node("build_citations", build_citations_node)

    # Entry point
    workflow.set_entry_point("contextualize_question")
    workflow.add_edge("contextualize_question", "retrieve_context")

    # Conditional branching based on context availability
    workflow.add_conditional_edges(
        "retrieve_context",
        check_context_condition,
        {
            "no_context": "insufficient_context",
            "has_context": "generate_answer"
        }
    )

    workflow.add_edge("insufficient_context", END)
    workflow.add_edge("generate_answer", "build_citations")
    workflow.add_edge("build_citations", END)

    return workflow.compile()
