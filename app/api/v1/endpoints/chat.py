from typing import Generator
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    GeneralChatRequest,
    GeneralChatResponse
)
from app.services.rag_service import RAGService

router = APIRouter()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def chat_with_documents(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    RAG Chat endpoint for querying uploaded documents.
    Retrieves grounded context, invokes Gemini via LangGraph, and returns
    a synthesized answer with structured citations.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or whitespace."
        )

    result = RAGService.run_rag(
        db=db,
        question=request.question.strip(),
        document_id=request.document_id,
        chat_id=request.chat_id,
        top_k=request.top_k
    )

    return ChatResponse(
        answer=result["answer"],
        citations=result["citations"],
        task_id=result["task_id"],
        token_usage=result.get("token_usage")
    )


@router.post("/general", response_model=GeneralChatResponse, status_code=status.HTTP_200_OK)
def general_chat(request: GeneralChatRequest):
    """
    General chat endpoint for non-document questions.
    Invokes Gemini directly without RAG retrieval or citations.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or whitespace."
        )

    prompt = (
        "You are Alex, an AI knowledge and research assistant. "
        "Answer the user's question clearly, concisely, and accurately.\n\n"
        f"User: {request.question.strip()}\n"
        "Alex:"
    )
    answer, token_usage = RAGService.generate_answer(prompt)
    return GeneralChatResponse(
        answer=answer,
        token_usage=token_usage
    )

