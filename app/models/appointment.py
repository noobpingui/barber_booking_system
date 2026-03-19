from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

STATUS_HOLD = "hold"
STATUS_CONFIRMED = "confirmed"
STATUS_CANCELLED = "cancelled"
STATUS_EXPIRED = "expired"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)

    # Slots are always 30 minutes; start_time is the only stored value.
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Optional notes field for future use (e.g. service type)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=STATUS_CONFIRMED
    )  # hold | confirmed | cancelled | expired

    # Hold management — set when status="hold", cleared on confirm/expire.
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Email verification — SHA-256 hash of the one-time confirm token.
    email_verification_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email_verification_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Cancellation via link — SHA-256 hash of the one-time cancel token.
    cancel_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cancel_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Audit timestamps
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="appointments")
