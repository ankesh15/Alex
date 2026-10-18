"""A single request-scoped database session shared by auth and protected routes."""
from typing import Generator
from sqlalchemy.orm import Session
from app.core.db import SessionLocal


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as db:
        yield db
