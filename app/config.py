import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "Alex — AI Knowledge & Research Assistant"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Google Gemini API Key & Model
    GOOGLE_API_KEY: str = Field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash")

    # Database Config
    DATABASE_URL: str = Field(default="postgresql://postgres:postgrespassword@postgres:5432/alex_db")

    # CORS Configuration
    ALLOWED_ORIGINS: str = Field(default="http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173")
    FRONTEND_URL: Optional[str] = Field(default=None)

    # Redis & Celery Config
    REDIS_URL: str = Field(default="redis://redis:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://redis:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://redis:6379/1")

    # Document Upload & Storage Config
    STORAGE_DIR: str = Field(default="storage/documents")
    MAX_UPLOAD_SIZE_MB: int = Field(default=20)

    # RAG Vector & Embedding Config
    EMBEDDING_MODEL: str = Field(default="BAAI/bge-small-en-v1.5")
    EMBEDDING_DIMENSION: int = Field(default=384)
    CHUNK_SIZE: int = Field(default=1000)
    CHUNK_OVERLAP: int = Field(default=150)
    RAG_TOP_K: int = Field(default=5)
    # Cosine distance threshold (0.0 is identical; <= threshold is considered relevant)
    RAG_SIMILARITY_THRESHOLD: float = Field(default=0.48)

    @property
    def cors_origins(self) -> List[str]:
        origins = [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        if self.FRONTEND_URL and self.FRONTEND_URL.strip():
            clean_url = self.FRONTEND_URL.strip().rstrip("/")
            if clean_url not in origins:
                origins.append(clean_url)
        return origins

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


settings = Settings()
