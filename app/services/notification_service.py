"""
Email notification service using Amazon SES.

All public functions are fire-and-forget: callers should wrap them in
try/except and log any exception — email failures must never fail a booking.

If SES_FROM_EMAIL is not configured the functions return immediately,
so the service is safely inert in local development.
"""

import logging
from datetime import datetime

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings

logger = logging.getLogger(__name__)

# Lazy singleton — created on first send attempt.
_ses_client = None


def _get_client():
    global _ses_client
    if _ses_client is not None:
        return _ses_client

    kwargs: dict = {"region_name": settings.aws_region}
    # Use explicit credentials when provided; otherwise boto3 falls back to
    # the EC2 instance's IAM role (preferred for production).
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

    _ses_client = boto3.client("ses", **kwargs)
    return _ses_client


def _send_email(to_email: str, subject: str, body: str) -> None:
    """Low-level SES send. Raises on failure — callers handle exceptions."""
    if not settings.ses_from_email:
        logger.debug("SES_FROM_EMAIL not configured — skipping email to %s", to_email)
        return

    _get_client().send_email(
        Source=settings.ses_from_email,
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
        },
    )
    logger.info("Email sent to %s — %s", to_email, subject)


# ── Public functions ───────────────────────────────────────────────────────────

def send_booking_confirmation_email(
    to_email: str,
    customer_name: str,
    start_time: datetime,
) -> None:
    """Send an appointment confirmation email to the customer."""
    date_str = start_time.strftime("%A, %B %d, %Y")
    time_str = start_time.strftime("%I:%M %p").lstrip("0")

    subject = f"Appointment confirmed — {date_str} at {time_str}"

    body = (
        f"Hi {customer_name},\n\n"
        f"Your appointment has been confirmed. Here are your details:\n\n"
        f"  Date:  {date_str}\n"
        f"  Time:  {time_str}\n\n"
        f"If you need to cancel, please do so at least "
        f"{settings.cancellation_window_hours} hour(s) before your appointment.\n\n"
        f"Thank you,\n"
        f"The Barber Shop"
    )

    _send_email(to_email, subject, body)


def send_booking_cancellation_email(
    to_email: str,
    customer_name: str,
    start_time: datetime,
) -> None:
    """Send an appointment cancellation notice to the customer."""
    date_str = start_time.strftime("%A, %B %d, %Y")
    time_str = start_time.strftime("%I:%M %p").lstrip("0")

    subject = f"Appointment cancelled — {date_str} at {time_str}"

    body = (
        f"Hi {customer_name},\n\n"
        f"Your appointment scheduled for {date_str} at {time_str} has been cancelled.\n\n"
        f"If you'd like to book a new appointment, you can do so at any time.\n\n"
        f"Thank you,\n"
        f"The Barber Shop"
    )

    _send_email(to_email, subject, body)
