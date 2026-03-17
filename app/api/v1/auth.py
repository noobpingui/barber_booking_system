from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import create_access_token, verify_password
from app.dependencies import get_current_user, get_db
from app.services.user_service import get_user_by_email

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

_COOKIE_NAME = "access_token"
_COOKIE_MAX_AGE = 60 * 60 * 8  # 8 hours


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str | None = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/auth/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, email.lower().strip())
    if user is None or not verify_password(password, user.password_hash):
        return RedirectResponse(url="/login?error=invalid_credentials", status_code=303)

    token = create_access_token({"sub": user.email, "role": user.role})
    response = RedirectResponse(url="/dashboard/", status_code=303)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=not settings.debug,  # HTTPS-only in production; allow HTTP in dev
        max_age=_COOKIE_MAX_AGE,
    )
    return response


@router.post("/auth/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key=_COOKIE_NAME)
    return response


@router.get("/auth/me")
def me(current_user=Depends(get_current_user)):
    """Returns current user info as JSON. Supports both cookie and Bearer token."""
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role}
