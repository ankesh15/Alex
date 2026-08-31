import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "Alex — AI Knowledge & Research Assistant"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Google Gemini API Key
    GOOGLE_API_KEY: str = Field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    GEMINI_MODEL: str = Field(default="models/gemini-3.6-flash")

    # Database Config
    DATABASE_URL: str = Field(default="postgresql://postgres:postgrespassword@postgres:5432/alex_db")

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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


settings = Settings()
