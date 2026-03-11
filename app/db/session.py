from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# check_same_thread is a SQLite-only argument that allows FastAPI's thread pool
# to reuse the same connection across threads. PostgreSQL handles this natively
# and will raise an error if this key is passed, so we only include it for SQLite.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args)

# autocommit=False  — we commit explicitly after each write operation.
# autoflush=False   — prevents SQLAlchemy from issuing surprise SQL mid-transaction.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
