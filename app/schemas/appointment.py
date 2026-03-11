from datetime import datetime, time, timedelta, timezone as tz

from pydantic import BaseModel, EmailStr, Field, field_validator

# Must stay in sync with _BUSINESS_START / _BUSINESS_END in appointment_service.py.
_SLOT_OPEN = time(9, 0)
_SLOT_CLOSE = time(20, 30)  # last valid start time; appointment ends at 21:00

_BOOKING_WINDOW = timedelta(minutes=30)  # must stay in sync with service
_LOCAL_TZ = tz(timedelta(hours=-6))      # must stay in sync with service


def _local_now() -> datetime:
    """Current time in the barber's timezone (UTC-6) as a naive datetime."""
    return datetime.now(_LOCAL_TZ).replace(tzinfo=None)


class AppointmentCreate(BaseModel):
    customer_id: int
    start_time: datetime
    notes: str | None = Field(default=None, max_length=255)

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: datetime) -> datetime:
        if v <= _local_now() + _BOOKING_WINDOW:
            raise ValueError("Appointments must be booked at least 30 minutes in advance.")

        if v.minute not in (0, 30) or v.second != 0 or v.microsecond != 0:
            raise ValueError(
                "Appointments must start on the hour or half-hour (e.g. 10:00 or 10:30)."
            )

        # Reject times outside business hours regardless of boundary alignment.
        slot_time = v.time().replace(second=0, microsecond=0)
        if not (_SLOT_OPEN <= slot_time <= _SLOT_CLOSE):
            raise ValueError(
                f"Appointments must be within business hours "
                f"({_SLOT_OPEN.strftime('%H:%M')}–{_SLOT_CLOSE.strftime('%H:%M')})."
            )

        return v


class AppointmentRead(BaseModel):
    id: int
    customer_id: int
    start_time: datetime
    notes: str | None
    status: str

    model_config = {"from_attributes": True}


class AppointmentCancel(BaseModel):
    # Email is used to verify ownership without requiring authentication.
    email: EmailStr


class AvailableSlot(BaseModel):
    start_time: datetime
