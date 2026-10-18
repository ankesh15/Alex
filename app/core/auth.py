"""Cookie sessions, CSRF/origin validation and PostgreSQL-backed auth throttling."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import secrets
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import case, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session
from app.api.dependencies import get_db
from app.config import settings
from app.models.user import User, UserSession, AuthRateLimit

COOKIE_NAME = "alex_session"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def session_cookie_name() -> str:
    # __Host- prevents subdomains from injecting a Domain-scoped production cookie.
    return f"__Host-{COOKIE_NAME}" if settings.SESSION_COOKIE_SECURE else COOKIE_NAME


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    email: str
    session_hash: str
    csrf_token: str
    expires_at: datetime


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def validate_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        raise HTTPException(status_code=403, detail="Request origin is not allowed.")
    if request.headers.get("sec-fetch-site") == "cross-site" and not origin:
        raise HTTPException(status_code=403, detail="Request origin is required.")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> AuthContext:
    token = request.cookies.get(session_cookie_name(), "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise HTTPException(status_code=401, detail="Authentication required.")
    digest = token_hash(token)
    record = db.query(UserSession, User).join(User, UserSession.user_id == User.id).filter(
        UserSession.token_hash == digest, UserSession.revoked_at.is_(None), User.is_active.is_(True)
    ).first()
    now = datetime.now(timezone.utc)
    if record is None:
        raise HTTPException(status_code=401, detail="Session is invalid or expired.")
    session, user = record
    if utc(session.expires_at) <= now or utc(session.last_seen_at) + timedelta(seconds=settings.SESSION_IDLE_SECONDS) <= now:
        raise HTTPException(status_code=401, detail="Session is invalid or expired.")
    if request.method not in SAFE_METHODS:
        validate_origin(request)
        csrf = request.headers.get("x-csrf-token", "")
        if not hmac.compare_digest(csrf.encode("utf-8"), session.csrf_token.encode("utf-8")):
            raise HTTPException(status_code=403, detail="CSRF validation failed. Refresh your session and try again.")
    context = AuthContext(user.id, user.email, digest, session.csrf_token, utc(session.expires_at))
    result = db.execute(update(UserSession).where(
        UserSession.token_hash == digest, UserSession.revoked_at.is_(None)
    ).values(last_seen_at=now))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=401, detail="Session is invalid or expired.")
    db.commit()
    return context


def throttle_auth(request: Request, db: Session) -> None:
    # Trust only the server's resolved peer address, not client-supplied forwarding headers.
    peer = request.client.host if request.client else "unknown"
    key = hashlib.sha256(f"auth:{peer}".encode()).hexdigest()
    now = datetime.now(timezone.utc)
    expired = AuthRateLimit.window_start <= now - timedelta(seconds=settings.AUTH_RATE_WINDOW_SECONDS)
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    statement = insert(AuthRateLimit).values(key=key, window_start=now, attempts=1).on_conflict_do_update(
        index_elements=[AuthRateLimit.key], set_={
            "window_start": case((expired, now), else_=AuthRateLimit.window_start),
            "attempts": case((expired, 1), else_=AuthRateLimit.attempts + 1),
        }
    ).returning(AuthRateLimit.attempts, AuthRateLimit.window_start)
    attempts, started = db.execute(statement).one()
    db.commit()
    if attempts > settings.AUTH_RATE_MAX_ATTEMPTS:
        retry_after = max(1, int((utc(started) + timedelta(seconds=settings.AUTH_RATE_WINDOW_SECONDS) - now).total_seconds()))
        raise HTTPException(status_code=429, detail="Too many authentication attempts. Please try again later.",
                            headers={"Retry-After": str(retry_after)})


def start_session(db: Session, user: User, request: Request, response: Response) -> dict:
    now = datetime.now(timezone.utc)
    old_token = request.cookies.get(session_cookie_name(), "")
    if re.fullmatch(r"[A-Za-z0-9_-]{43}", old_token):
        db.execute(update(UserSession).where(UserSession.token_hash == token_hash(old_token)).values(revoked_at=now))
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    expires = now + timedelta(seconds=settings.SESSION_MAX_AGE_SECONDS)
    user_id, email = user.id, user.email
    db.add(UserSession(token_hash=token_hash(token), user_id=user_id, csrf_token=csrf,
                       created_at=now, last_seen_at=now, expires_at=expires))
    db.commit()
    response.set_cookie(session_cookie_name(), token, max_age=settings.SESSION_MAX_AGE_SECONDS, expires=expires,
                        httponly=True, secure=settings.SESSION_COOKIE_SECURE,
                        samesite=settings.SESSION_COOKIE_SAMESITE, path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"user": {"id": user_id, "email": email}, "csrf_token": csrf, "expires_at": expires}
