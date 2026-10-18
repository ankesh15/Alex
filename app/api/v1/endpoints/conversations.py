from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.dependencies import get_db
from app.core.auth import AuthContext, get_current_user
from app.api.schemas import ConversationCreate, ConversationRename, ConversationResponse
from app.services.conversation_service import ConversationService

router = APIRouter()


@router.post("", status_code=201, response_model=ConversationResponse)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db),
                        user: AuthContext = Depends(get_current_user)):
    return ConversationService.create(db, user.user_id, payload.title)


@router.get("")
def list_conversations(limit: int = Query(25, ge=1, le=100), cursor: str | None = Query(None, max_length=512),
                       db: Session = Depends(get_db), user: AuthContext = Depends(get_current_user)):
    return ConversationService.list(db, user.user_id, limit, cursor)


@router.get("/{chat_id}")
def get_conversation(chat_id: str, db: Session = Depends(get_db), user: AuthContext = Depends(get_current_user)):
    return ConversationService.retrieve(db, user.user_id, chat_id)


@router.patch("/{chat_id}", response_model=ConversationResponse)
def rename_conversation(chat_id: str, payload: ConversationRename, db: Session = Depends(get_db),
                        user: AuthContext = Depends(get_current_user)):
    return ConversationService.rename(db, user.user_id, chat_id, payload.title)


@router.get("/{chat_id}/messages")
def get_messages(chat_id: str, limit: int = Query(25, ge=1, le=100),
                 before_turn: int | None = Query(None, ge=1), through_turn: int | None = Query(None, ge=0),
                 db: Session = Depends(get_db), user: AuthContext = Depends(get_current_user)):
    return ConversationService.messages(db, user.user_id, chat_id, limit, before_turn, through_turn)


@router.delete("/{chat_id}")
def delete_conversation(chat_id: str, db: Session = Depends(get_db), user: AuthContext = Depends(get_current_user)):
    return ConversationService.delete(db, user.user_id, chat_id)
