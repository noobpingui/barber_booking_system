from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

STATUS_CONFIRMED = "confirmed"
STATUS_CANCELLED = "cancelled"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)

    # Slots are always 30 minutes; start_time is the only stored value.
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Optional notes field for future use (e.g. service type)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="confirmed"
    )  # confirmed | cancelled

    customer: Mapped["Customer"] = relationship(back_populates="appointments")
