from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.v1 import appointments, auth, booking, customers, dashboard
from app.config import settings
from app.db.session import engine
from app.models import base  # noqa: F401 — ensures Base is populated
import app.models  # noqa: F401 — triggers __init__.py, registering all models


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Development convenience: auto-create tables on startup.
    # Production: run `alembic upgrade head` before starting the server instead.
    base.Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Barber Booking System",
    description="API for managing barber appointments",
    version="0.1.0",
    lifespan=lifespan,
    # Disable interactive API docs in production — not needed and reduces attack surface.
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# JSON API endpoints
app.include_router(customers.router, prefix="/api/v1")
app.include_router(appointments.router, prefix="/api/v1")

# HTML views
app.include_router(auth.router)      # auth:            /login, /auth/login, /auth/logout, /auth/me
app.include_router(booking.router)   # customer-facing: /booking/
app.include_router(dashboard.router) # barber-facing:   /dashboard/


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard/")


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
