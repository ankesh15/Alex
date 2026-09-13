from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class TokenUsageSchema(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class AsyncJobResponse(BaseModel):
    message: str
    task_id: str
    status: str = "queued"


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: dict | None = None
    token_usage: TokenUsageSchema | None = None


# Document Management Schemas
class DocumentResponse(BaseModel):
    id: str
    chat_id: Optional[str] = None
    filename: str
    file_type: str
    file_size: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


class DocumentDetailResponse(DocumentResponse):
    page_count: int = 0


# Chat & RAG Schemas
class ChatRequest(BaseModel):
    question: str
    document_id: Optional[str] = None
    chat_id: Optional[str] = None
    top_k: Optional[int] = None


class CitationSchema(BaseModel):
    document_id: str
    filename: str
    page_number: Optional[int] = None
    chunk_id: str
    relevance_score: float


class ChatResponse(BaseModel):
    answer: str
    citations: List[CitationSchema] = []
    task_id: str
    token_usage: Optional[TokenUsageSchema] = None


class GeneralChatRequest(BaseModel):
    question: str


class GeneralChatResponse(BaseModel):
    answer: str
    token_usage: Optional[TokenUsageSchema] = None

