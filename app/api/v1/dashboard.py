import logging
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_current_user_web, get_db
from app.models.appointment import STATUS_CANCELLED, STATUS_CONFIRMED
from app.models.user import User
from app.services import appointment_service, customer_service, notification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")

# All valid slot times for the "Block a slot" dropdown (09:00–20:30).
_BLOCK_SLOT_TIMES: list[str] = []
_t = datetime.combine(date.today(), time(9, 0))
_end = datetime.combine(date.today(), time(21, 0))
while _t < _end:
    _BLOCK_SLOT_TIMES.append(_t.strftime("%H:%M"))
    _t += timedelta(minutes=30)


def _build_events(appointments, blocked_slots) -> list[dict]:
    """Merge appointments and blocked slots into a single list sorted by start time."""
    events = []
    for a in appointments:
        events.append({"kind": "appointment", "start_time": a.start_time, "appt": a})
    for b in blocked_slots:
        events.append({"kind": "blocked", "start_time": b.start_time, "block": b})
    events.sort(key=lambda e: e["start_time"])
    return events


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    target_date: date | None = None,
    block_error: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user_web),
):
    if target_date is None:
        target_date = date.today()

    appointment_service.expire_old_holds(db)
    appointments = appointment_service.get_appointments_by_date(db, target_date)
    blocked_slots = appointment_service.get_blocked_slots_by_date(db, target_date)

    confirmed = sum(1 for a in appointments if a.status == STATUS_CONFIRMED)
    cancelled = sum(1 for a in appointments if a.status == STATUS_CANCELLED)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "events": _build_events(appointments, blocked_slots),
            "target_date": target_date,
            "prev_date": target_date - timedelta(days=1),
            "next_date": target_date + timedelta(days=1),
            "confirmed_count": confirmed,
            "cancelled_count": cancelled,
            "blocked_count": len(blocked_slots),
            "slot_times": _BLOCK_SLOT_TIMES,
            "block_error": block_error,
        },
    )


@router.post("/cancel/{appointment_id}")
def cancel_appointment(
    appointment_id: int,
    target_date: date = Form(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user_web),
):
    appointment, reason = appointment_service.barber_cancel_appointment(db, appointment_id)

    if reason == "ok" and appointment is not None:
        customer = customer_service.get_customer_by_id(db, appointment.customer_id)
        if customer:
            try:
                notification_service.send_booking_cancellation_email(
                    to_email=customer.email,
                    customer_name=customer.full_name,
                    start_time=appointment.start_time,
                )
            except Exception:
                logger.exception(
                    "Failed to send cancellation email for appointment %d", appointment_id
                )

    return RedirectResponse(url=f"/dashboard/?target_date={target_date}", status_code=303)


@router.post("/block")
def block_slot(
    target_date: date = Form(...),
    slot_time: str = Form(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user_web),
):
    try:
        start_time = datetime.combine(target_date, datetime.strptime(slot_time, "%H:%M").time())
    except ValueError:
        return RedirectResponse(
            url=f"/dashboard/?target_date={target_date}&block_error=invalid",
            status_code=303,
        )

    _, reason = appointment_service.block_slot(db, start_time)

    if reason == "already_booked":
        return RedirectResponse(
            url=f"/dashboard/?target_date={target_date}&block_error=already_booked",
            status_code=303,
        )

    return RedirectResponse(url=f"/dashboard/?target_date={target_date}", status_code=303)


@router.post("/unblock/{blocked_slot_id}")
def unblock_slot(
    blocked_slot_id: int,
    target_date: date = Form(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user_web),
):
    appointment_service.unblock_slot(db, blocked_slot_id)
    return RedirectResponse(url=f"/dashboard/?target_date={target_date}", status_code=303)
