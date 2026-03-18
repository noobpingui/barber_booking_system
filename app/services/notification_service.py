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


def _send_email(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """Low-level SES send. Raises on failure — callers handle exceptions."""
    if not settings.ses_from_email:
        logger.debug("SES_FROM_EMAIL not configured — skipping email to %s", to_email)
        return

    _get_client().send_email(
        Source=f"Bailey Barbershop <{settings.ses_from_email}>",
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": text_body, "Charset": "UTF-8"},
                "Html": {"Data": html_body, "Charset": "UTF-8"},
            },
        },
    )
    logger.info("Email sent to %s — %s", to_email, subject)


# ── HTML builders ──────────────────────────────────────────────────────────────

def _base_html(title: str, subtitle: str, customer_name: str, date_str: str, time_str: str, message: str) -> str:
    """
    Builds a card-style HTML email body with inline styles for broad
    email-client compatibility (Gmail, Outlook, Apple Mail).
    """
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:#f4f4f5; font-family:Arial,Helvetica,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f4f4f5; padding:40px 16px;">
    <tr>
      <td align="center">

        <!-- Card -->
        <table cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px; width:100%; background-color:#ffffff;
                      border-radius:8px; overflow:hidden;
                      border:1px solid #e5e7eb;">

          <!-- Header -->
          <tr>
            <td align="center" bgcolor="#111111"
                style="background-color:#111111; padding:28px 32px;">
              <span style="color:#ffffff; font-size:20px; font-weight:bold;
                           letter-spacing:1px;">
                &#9988; Bailey Barbershop
              </span>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px 40px;">

              <!-- Title -->
              <h1 style="margin:0 0 6px 0; font-size:22px; font-weight:bold;
                         color:#111111; line-height:1.2;">
                {title}
              </h1>
              <p style="margin:0 0 28px 0; font-size:14px; color:#6b7280;">
                {subtitle}
              </p>

              <!-- Greeting -->
              <p style="margin:0 0 24px 0; font-size:15px; color:#374151;">
                Hola <strong>{customer_name}</strong>,
              </p>

              <!-- Detail card -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background-color:#f9fafb; border-radius:6px;
                            border:1px solid #e5e7eb; margin-bottom:28px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <table width="100%" cellpadding="0" cellspacing="0" border="0">

                      <!-- Date row -->
                      <tr>
                        <td style="padding-bottom:14px;">
                          <span style="display:block; font-size:11px; font-weight:bold;
                                       text-transform:uppercase; letter-spacing:0.8px;
                                       color:#9ca3af; margin-bottom:4px;">
                            Fecha
                          </span>
                          <span style="font-size:16px; font-weight:bold; color:#111111;">
                            {date_str}
                          </span>
                        </td>
                      </tr>

                      <!-- Divider -->
                      <tr>
                        <td style="border-top:1px solid #e5e7eb;"></td>
                      </tr>

                      <!-- Time row -->
                      <tr>
                        <td style="padding-top:14px;">
                          <span style="display:block; font-size:11px; font-weight:bold;
                                       text-transform:uppercase; letter-spacing:0.8px;
                                       color:#9ca3af; margin-bottom:4px;">
                            Hora
                          </span>
                          <span style="font-size:16px; font-weight:bold; color:#111111;">
                            {time_str}
                          </span>
                        </td>
                      </tr>

                    </table>
                  </td>
                </tr>
              </table>

              <!-- Message -->
              <p style="margin:0; font-size:14px; color:#6b7280; line-height:1.6;">
                {message}
              </p>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td align="center"
                style="padding:20px 32px; border-top:1px solid #e5e7eb;
                       background-color:#f9fafb;">
              <p style="margin:0; font-size:12px; color:#9ca3af; line-height:1.5;">
                Bailey Barbershop<br>
                Este es un mensaje autom&aacute;tico, por favor no respondas a este correo.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""


def _confirmation_html(customer_name: str, date_str: str, time_str: str) -> str:
    message = (
        f"Si necesitas cancelar tu cita, hazlo con al menos "
        f"<strong>{settings.cancellation_window_hours} hora(s)</strong> de anticipaci&oacute;n."
    )
    return _base_html(
        title="Cita Confirmada",
        subtitle="Tu reserva ha sido registrada con &eacute;xito.",
        customer_name=customer_name,
        date_str=date_str,
        time_str=time_str,
        message=message,
    )


def _cancellation_html(customer_name: str, date_str: str, time_str: str) -> str:
    message = (
        "Si deseas agendar una nueva cita, puedes hacerlo en cualquier momento "
        "a trav&eacute;s de nuestra p&aacute;gina de reservas."
    )
    return _base_html(
        title="Cita Cancelada",
        subtitle="Tu cita ha sido cancelada correctamente.",
        customer_name=customer_name,
        date_str=date_str,
        time_str=time_str,
        message=message,
    )


# ── Public functions ───────────────────────────────────────────────────────────

def send_booking_confirmation_email(
    to_email: str,
    customer_name: str,
    start_time: datetime,
) -> None:
    """Send an appointment confirmation email to the customer."""
    date_str = start_time.strftime("%A, %d de %B de %Y")
    time_str = start_time.strftime("%I:%M %p").lstrip("0")

    subject = f"Cita confirmada — {date_str} a las {time_str}"

    text_body = (
        f"Hola {customer_name},\n\n"
        f"Tu cita ha sido confirmada. Aquí están los detalles:\n\n"
        f"  Fecha:  {date_str}\n"
        f"  Hora:   {time_str}\n\n"
        f"Si necesitas cancelar, hazlo con al menos "
        f"{settings.cancellation_window_hours} hora(s) de anticipación.\n\n"
        f"Gracias por tu preferencia,\n"
        f"Bailey Barbershop"
    )

    _send_email(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=_confirmation_html(customer_name, date_str, time_str),
    )


def send_booking_cancellation_email(
    to_email: str,
    customer_name: str,
    start_time: datetime,
) -> None:
    """Send an appointment cancellation notice to the customer."""
    date_str = start_time.strftime("%A, %d de %B de %Y")
    time_str = start_time.strftime("%I:%M %p").lstrip("0")

    subject = f"Cita cancelada — {date_str} a las {time_str}"

    text_body = (
        f"Hola {customer_name},\n\n"
        f"Tu cita programada para el {date_str} a las {time_str} ha sido cancelada.\n\n"
        f"Si deseas agendar una nueva cita, puedes hacerlo en cualquier momento.\n\n"
        f"Gracias por tu preferencia,\n"
        f"Bailey Barbershop"
    )

    _send_email(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=_cancellation_html(customer_name, date_str, time_str),
    )
