from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.dependencies import get_db
from app.api.schemas import LoginRequest, SignupRequest, AuthResponse
from app.core.auth import AuthContext, session_cookie_name, get_current_user, validate_origin, throttle_auth, start_session
from app.core.passwords import hash_password, verify_password, DUMMY_PASSWORD_HASH
from app.config import settings
from app.models.user import User, UserSession

router = APIRouter()


@router.post("/signup", response_model=AuthResponse, status_code=201)
def signup(payload: SignupRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    validate_origin(request)
    throttle_auth(request, db)
    password_hash = hash_password(payload.password.get_secret_value())
    user = User(email=payload.email, password_hash=password_hash)
    try:
        db.add(user)
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Unable to create an account with that email.") from exc
    return start_session(db, user, request, response)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    validate_origin(request)
    throttle_auth(request, db)
    user = db.query(User).filter(User.email == payload.email).first()
    valid = verify_password(payload.password.get_secret_value(), user.password_hash if user else DUMMY_PASSWORD_HASH)
    if not valid or user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return start_session(db, user, request, response)


@router.get("/me", response_model=AuthResponse)
def current_session(response: Response, user: AuthContext = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return {"user": {"id": user.user_id, "email": user.email}, "csrf_token": user.csrf_token,
            "expires_at": user.expires_at}


@router.post("/logout", status_code=204)
def logout(response: Response, user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(update(UserSession).where(UserSession.token_hash == user.session_hash).values(
        revoked_at=datetime.now(timezone.utc)))
    db.commit()
    response.delete_cookie(session_cookie_name(), path="/", secure=settings.SESSION_COOKIE_SECURE,
                           httponly=True, samesite=settings.SESSION_COOKIE_SAMESITE)
    response.headers["Cache-Control"] = "no-store"
