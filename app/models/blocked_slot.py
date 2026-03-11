from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BlockedSlot(Base):
    __tablename__ = "blocked_slots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Unique constraint: only one block record per slot.
    start_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, unique=True, index=True
    )
