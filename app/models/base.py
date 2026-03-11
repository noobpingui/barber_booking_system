from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    All ORM models inherit from this class.
    Alembic's env.py imports Base.metadata to detect schema changes.
    """
    pass
