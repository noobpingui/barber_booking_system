from collections.abc import Generator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.services.user_service import get_user_by_email


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session per request.
    The session is always closed when the request ends, even on errors.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _extract_token(request: Request) -> str | None:
    """Read JWT from HTTP-only cookie first, then Authorization header (Bearer)."""
    token = request.cookies.get("access_token")
    if token:
        return token
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def _resolve_user(token: str, db: Session) -> User | None:
    payload = decode_access_token(token)
    if payload is None:
        return None
    email: str | None = payload.get("sub")
    if not email:
        return None
    return get_user_by_email(db, email)


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    """For JSON API endpoints — returns 401 if not authenticated."""
    token = _extract_token(request)
    user = _resolve_user(token, db) if token else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def get_current_user_web(
    request: Request, db: Session = Depends(get_db)
) -> User:
    """For HTML dashboard routes — redirects to /login if not authenticated."""
    token = _extract_token(request)
    user = _resolve_user(token, db) if token else None
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user
