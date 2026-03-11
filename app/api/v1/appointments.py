from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.schemas.appointment import AppointmentCancel, AppointmentCreate, AppointmentRead, AvailableSlot
from app.services import appointment_service, customer_service

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("/available-slots", response_model=list[AvailableSlot])
def available_slots(target_date: date, db: Session = Depends(get_db)):
    """
    Return all open 30-minute slots for the given date.
    Query param: target_date (YYYY-MM-DD)
    """
    slots = appointment_service.get_available_slots(db, target_date)
    return [{"start_time": s} for s in slots]


@router.post("/", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(data: AppointmentCreate, db: Session = Depends(get_db)):
    # Hard guard 1: customer must exist before a slot is reserved for them.
    if not customer_service.get_customer_by_id(db, data.customer_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )
    # Hard guard 2: re-check availability at write time (race condition safety).
    if appointment_service.is_slot_taken(db, data.start_time):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This time slot is already booked.",
        )
    return appointment_service.create_appointment(db, data)


@router.get("/", response_model=list[AppointmentRead])
def list_appointments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return appointment_service.get_all_appointments(db, skip=skip, limit=limit)


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appointment = appointment_service.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")
    return appointment


@router.patch("/{appointment_id}/cancel", response_model=AppointmentRead)
def cancel_appointment(
    appointment_id: int,
    data: AppointmentCancel,
    db: Session = Depends(get_db),
):
    appointment, reason = appointment_service.cancel_appointment(db, appointment_id, data.email)

    if reason == "not_found":
        # Intentionally vague: do not reveal whether the ID exists to an unauthorized caller.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or does not belong to this email.",
        )
    if reason == "already_cancelled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment is already cancelled.",
        )
    if reason == "window_passed":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Cancellations must be made at least "
                f"{settings.cancellation_window_hours} hours before the appointment."
            ),
        )
    return appointment
