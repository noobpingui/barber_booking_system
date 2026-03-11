from datetime import date, datetime, time, timedelta, timezone as tz

from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.appointment import STATUS_CANCELLED, STATUS_CONFIRMED, Appointment
from app.models.blocked_slot import BlockedSlot
from app.models.customer import Customer
from app.schemas.appointment import AppointmentCreate

# Business hours: 09:00–21:00, 7 days a week. Last slot starts at 20:30.
# Move to config when multi-staff or configurable hours are needed.
_BUSINESS_START = time(9, 0)
_BUSINESS_END = time(21, 0)
_SLOT_DURATION = timedelta(minutes=30)

# Minimum lead time: customers must book at least this far in advance.
_BOOKING_WINDOW = timedelta(minutes=30)

# Barber's local timezone: UTC-6 (fixed offset — no DST adjustment).
# All appointment times in the DB are stored as naive local (UTC-6) datetimes.
_LOCAL_TZ = tz(timedelta(hours=-6))


def _local_now() -> datetime:
    """Current time in the barber's timezone (UTC-6) as a naive datetime."""
    return datetime.now(_LOCAL_TZ).replace(tzinfo=None)


def _local_today() -> date:
    """Today's date in the barber's timezone (UTC-6)."""
    return datetime.now(_LOCAL_TZ).date()


def get_booking_window() -> tuple[date, date]:
    """Return (today, max_date) for the customer-facing 7-day booking window."""
    today = _local_today()
    return today, today + timedelta(days=6)


def _day_bounds(target_date: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(target_date, _BUSINESS_START),
        datetime.combine(target_date, _BUSINESS_END),
    )


# ── Appointment queries ────────────────────────────────────────────────────────

def get_appointment_by_id(db: Session, appointment_id: int) -> Appointment | None:
    return db.query(Appointment).filter(Appointment.id == appointment_id).first()


def get_all_appointments(db: Session, skip: int = 0, limit: int = 100) -> list[Appointment]:
    return (
        db.query(Appointment)
        .order_by(Appointment.start_time)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_appointments_by_date(db: Session, target_date: date) -> list[Appointment]:
    """Return all appointments for a given date, sorted by start time, with customer loaded."""
    day_start, day_end = _day_bounds(target_date)
    return (
        db.query(Appointment)
        .options(joinedload(Appointment.customer))
        .filter(
            Appointment.start_time >= day_start,
            Appointment.start_time < day_end,
        )
        .order_by(Appointment.start_time)
        .all()
    )


# ── Slot availability ──────────────────────────────────────────────────────────

def is_slot_taken(db: Session, start_time: datetime) -> bool:
    """Return True if the slot is occupied by a confirmed appointment or a block."""
    confirmed = (
        db.query(Appointment)
        .filter(
            Appointment.start_time == start_time,
            Appointment.status == STATUS_CONFIRMED,
        )
        .first()
        is not None
    )
    if confirmed:
        return True
    return (
        db.query(BlockedSlot).filter(BlockedSlot.start_time == start_time).first()
        is not None
    )


def get_available_slots(db: Session, target_date: date) -> list[datetime]:
    """
    Return all bookable 30-minute slots for target_date.
    Excludes slots that are confirmed, blocked, or within the booking window.
    """
    day_start, day_end = _day_bounds(target_date)

    all_slots: list[datetime] = []
    current = day_start
    while current < day_end:
        all_slots.append(current)
        current += _SLOT_DURATION

    # Confirmed bookings for this date
    booked: set[datetime] = {
        row.start_time
        for row in db.query(Appointment.start_time)
        .filter(
            Appointment.start_time >= day_start,
            Appointment.start_time < day_end,
            Appointment.status == STATUS_CONFIRMED,
        )
        .all()
    }

    # Manually blocked slots for this date
    blocked: set[datetime] = {
        row.start_time
        for row in db.query(BlockedSlot.start_time)
        .filter(
            BlockedSlot.start_time >= day_start,
            BlockedSlot.start_time < day_end,
        )
        .all()
    }

    # Only expose slots at least _BOOKING_WINDOW ahead of now
    cutoff = _local_now() + _BOOKING_WINDOW
    return [s for s in all_slots if s not in booked and s not in blocked and s > cutoff]


def has_appointment_in_booking_window(db: Session, customer_id: int) -> bool:
    """
    Return True if the customer already has a confirmed appointment within the
    rolling 7-day booking window (today through today+6, in local time).
    Customers may only hold one appointment per 7-day window.
    """
    today = _local_today()
    window_start = datetime.combine(today, time.min)
    window_end = datetime.combine(today + timedelta(days=7), time.min)
    return (
        db.query(Appointment)
        .filter(
            Appointment.customer_id == customer_id,
            Appointment.status == STATUS_CONFIRMED,
            Appointment.start_time >= window_start,
            Appointment.start_time < window_end,
        )
        .first()
        is not None
    )


# ── Appointment writes ─────────────────────────────────────────────────────────

def create_appointment(db: Session, data: AppointmentCreate) -> Appointment:
    appointment = Appointment(
        customer_id=data.customer_id,
        start_time=data.start_time,
        notes=data.notes,
        status=STATUS_CONFIRMED,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def cancel_appointment(
    db: Session, appointment_id: int, email: str
) -> tuple[Appointment | None, str]:
    """
    Cancel an appointment. Returns (appointment, reason) where reason is one of:
      "ok"                — successfully cancelled
      "not_found"         — appointment not found, or email does not match owner
      "already_cancelled" — appointment is already cancelled
      "window_passed"     — cancellation window has expired

    Ownership and existence share the same "not_found" reason intentionally:
    an unauthorized caller should not be able to tell whether an ID exists.
    """
    appointment = get_appointment_by_id(db, appointment_id)
    if appointment is None:
        return None, "not_found"

    customer = db.query(Customer).filter(Customer.id == appointment.customer_id).first()
    if customer is None or customer.email.lower() != email.lower():
        return None, "not_found"

    if appointment.status == STATUS_CANCELLED:
        return appointment, "already_cancelled"

    cutoff = appointment.start_time - timedelta(hours=settings.cancellation_window_hours)
    if _local_now() >= cutoff:
        return appointment, "window_passed"

    appointment.status = STATUS_CANCELLED
    db.commit()
    db.refresh(appointment)
    return appointment, "ok"


def barber_cancel_appointment(db: Session, appointment_id: int) -> tuple[Appointment | None, str]:
    """
    Cancel an appointment from the barber dashboard.
    Skips the email ownership check — the barber has full authority.
    Returns (appointment, reason): "ok", "not_found", or "already_cancelled".
    """
    appointment = get_appointment_by_id(db, appointment_id)
    if appointment is None:
        return None, "not_found"
    if appointment.status == STATUS_CANCELLED:
        return appointment, "already_cancelled"
    appointment.status = STATUS_CANCELLED
    db.commit()
    db.refresh(appointment)
    return appointment, "ok"


# ── Blocked slots ──────────────────────────────────────────────────────────────

def get_blocked_slots_by_date(db: Session, target_date: date) -> list[BlockedSlot]:
    day_start, day_end = _day_bounds(target_date)
    return (
        db.query(BlockedSlot)
        .filter(
            BlockedSlot.start_time >= day_start,
            BlockedSlot.start_time < day_end,
        )
        .order_by(BlockedSlot.start_time)
        .all()
    )


def block_slot(db: Session, start_time: datetime) -> tuple[BlockedSlot | None, str]:
    """
    Block a slot from the barber dashboard.
    Returns (blocked_slot, reason): "ok", "already_blocked", or "already_booked".
    """
    existing = db.query(BlockedSlot).filter(BlockedSlot.start_time == start_time).first()
    if existing:
        return existing, "already_blocked"

    if (
        db.query(Appointment)
        .filter(
            Appointment.start_time == start_time,
            Appointment.status == STATUS_CONFIRMED,
        )
        .first()
        is not None
    ):
        return None, "already_booked"

    slot = BlockedSlot(start_time=start_time)
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot, "ok"


def unblock_slot(db: Session, blocked_slot_id: int) -> tuple[BlockedSlot | None, str]:
    """Remove a manual block. Returns (slot, reason): "ok" or "not_found"."""
    slot = db.query(BlockedSlot).filter(BlockedSlot.id == blocked_slot_id).first()
    if slot is None:
        return None, "not_found"
    db.delete(slot)
    db.commit()
    return slot, "ok"
