from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)
    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        import re
        value = value.strip().lower()
        if not value.isascii() or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address.")
        return value


class SignupRequest(LoginRequest):
    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if len(password) < 12 or not password.strip():
            raise ValueError("Password must contain at least 12 characters and cannot be all whitespace.")
        return value


class AuthUserResponse(BaseModel):
    id: str
    email: str


class AuthResponse(BaseModel):
    user: AuthUserResponse
    csrf_token: str
    expires_at: datetime


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
    model_config = ConfigDict(extra="forbid")
    question: str = Field(max_length=12000)
    document_id: Optional[str] = Field(default=None, min_length=1, max_length=36)
    chat_id: Optional[str] = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    top_k: Optional[int] = Field(default=None, ge=1, le=100)


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
    model_config = ConfigDict(extra="forbid")
    question: str = Field(max_length=12000)
    chat_id: Optional[str] = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class GeneralChatResponse(BaseModel):
    answer: str
    token_usage: Optional[TokenUsageSchema] = None


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        title = " ".join(value.split())
        if not title:
            raise ValueError("Conversation title cannot be empty.")
        return title


class ConversationRename(ConversationCreate):
    title: str = Field(min_length=1, max_length=120)


class ConversationResponse(BaseModel):
    id: str
    title: str
    revision: int
    created_at: datetime
    updated_at: datetime
