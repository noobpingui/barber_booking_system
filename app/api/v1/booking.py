import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session, joinedload

from app.dependencies import get_db
from app.models.appointment import Appointment as ApptModel
from app.schemas.appointment import AppointmentCreate
from app.schemas.customer import CustomerCreate
from app.services import appointment_service, customer_service, notification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/booking", tags=["booking"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def booking_page(
    request: Request,
    error: str | None = None,
):
    today, max_date = appointment_service.get_booking_window()
    return templates.TemplateResponse(
        "booking.html",
        {
            "request": request,
            "error": error,
            "today_str": today.isoformat(),
            "max_date_str": max_date.isoformat(),
        },
    )


@router.post("/", response_class=HTMLResponse)
def submit_booking(
    request: Request,
    start_time: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    today, max_date = appointment_service.get_booking_window()

    # Parse the ISO datetime string submitted by the form.
    try:
        slot_dt = datetime.fromisoformat(start_time)
    except ValueError:
        return RedirectResponse(url="/booking/?error=invalid_slot", status_code=303)

    # Server-side: reject dates outside the 7-day booking window.
    if not (today <= slot_dt.date() <= max_date):
        return RedirectResponse(url="/booking/?error=invalid_slot", status_code=303)

    # Validate customer fields via Pydantic.
    try:
        customer_data = CustomerCreate(full_name=full_name, email=email, phone=phone)
    except ValidationError:
        return RedirectResponse(url="/booking/?error=invalid_details", status_code=303)

    # Validate the appointment slot (business hours, 30-min boundary, lead time).
    try:
        appt_data = AppointmentCreate(
            customer_id=0,  # placeholder — set below after customer lookup
            start_time=slot_dt,
            notes=notes or None,
        )
    except ValidationError:
        return RedirectResponse(url="/booking/?error=invalid_slot", status_code=303)

    # Hard check: slot must still be free at write time.
    if appointment_service.is_slot_taken(db, slot_dt):
        return RedirectResponse(url="/booking/?error=slot_taken", status_code=303)

    customer = customer_service.get_or_create_customer(db, customer_data)

    # Hard check: one appointment per customer per 7-day rolling window.
    if appointment_service.has_appointment_in_booking_window(db, customer.id):
        return RedirectResponse(url="/booking/?error=week_limit", status_code=303)

    appt_data.customer_id = customer.id
    appointment = appointment_service.create_appointment(db, appt_data)

    try:
        notification_service.send_booking_confirmation_email(
            to_email=customer.email,
            customer_name=customer.full_name,
            start_time=appointment.start_time,
        )
    except Exception:
        logger.exception(
            "Failed to send booking confirmation email for appointment %d", appointment.id
        )

    return RedirectResponse(
        url=f"/booking/confirmation?id={appointment.id}", status_code=303
    )


@router.get("/confirmation", response_class=HTMLResponse)
def booking_confirmation(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
):
    appointment = (
        db.query(ApptModel)
        .options(joinedload(ApptModel.customer))
        .filter(ApptModel.id == id)
        .first()
    )
    if appointment is None:
        return RedirectResponse(url="/booking/", status_code=303)

    return templates.TemplateResponse(
        "booking_confirmation.html",
        {"request": request, "appointment": appointment},
    )
