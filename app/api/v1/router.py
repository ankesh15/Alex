from fastapi import APIRouter, Depends
from app.api.v1.endpoints import documents, chat, auth, conversations
from app.core.auth import get_current_user

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# Router-level protection also covers any future chat/document operations.
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"], dependencies=[Depends(get_current_user)])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat / RAG"], dependencies=[Depends(get_current_user)])
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"],
                          dependencies=[Depends(get_current_user)])
