"""
Email notification service.

Supports two providers, selected via EMAIL_PROVIDER in .env:
  - "resend"  (default) — uses the Resend API over HTTPS
  - "ses"               — uses AWS SES via boto3

Public functions are fire-and-forget: callers must wrap them in try/except
and log any exception — email failures must never fail a booking operation.

If EMAIL_FROM is not configured the functions return immediately,
so the service is safely inert in local development.
"""

import logging
from datetime import datetime

import boto3
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_SENDER_NAME = "Bailey Barbershop"
_RESEND_API_URL = "https://api.resend.com/emails"

# ── Date/time formatting ───────────────────────────────────────────────────────

_DAYS_ES = (
    "lunes", "martes", "miércoles", "jueves",
    "viernes", "sábado", "domingo",
)
_MONTHS_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def _format_date_es(dt: datetime) -> str:
    """Return a fully Spanish date string, e.g. 'miércoles, 18 de marzo de 2026'."""
    day_name = _DAYS_ES[dt.weekday()]
    month_name = _MONTHS_ES[dt.month - 1]
    return f"{day_name}, {dt.day} de {month_name} de {dt.year}"


def _format_time(dt: datetime) -> str:
    """Return a clean 12-hour time string, e.g. '9:30 AM'."""
    return dt.strftime("%I:%M %p").lstrip("0")


# ── Provider implementations ───────────────────────────────────────────────────

def _send_with_resend(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """Send via the Resend HTTP API. Raises on non-2xx response."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured — skipping email to %s", to_email)
        return

    response = httpx.post(
        _RESEND_API_URL,
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json={
            "from": f"{_SENDER_NAME} <{settings.email_from}>",
            "to": [to_email],
            "subject": subject,
            "text": text_body,
            "html": html_body,
        },
        timeout=10,
    )
    if response.is_error:
        logger.error(
            "Resend API error — status: %s, body: %s",
            response.status_code,
            response.text,
        )
    response.raise_for_status()
    logger.info("Email sent via Resend to %s — %s", to_email, subject)


# Lazy SES client singleton — created on first use, reused across requests.
_ses_client = None


def _get_ses_client():
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


def _send_with_ses(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """Send via AWS SES. Raises on failure."""
    _get_ses_client().send_email(
        Source=f"{_SENDER_NAME} <{settings.email_from}>",
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": text_body, "Charset": "UTF-8"},
                "Html": {"Data": html_body, "Charset": "UTF-8"},
            },
        },
    )
    logger.info("Email sent via SES to %s — %s", to_email, subject)


def _send_email(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """Route to the configured provider. Returns immediately if EMAIL_FROM is unset."""
    if not settings.email_from:
        logger.debug("EMAIL_FROM not configured — skipping email to %s", to_email)
        return

    if settings.email_provider == "resend":
        _send_with_resend(to_email, subject, text_body, html_body)
    elif settings.email_provider == "ses":
        _send_with_ses(to_email, subject, text_body, html_body)
    else:
        logger.warning(
            "Unknown EMAIL_PROVIDER '%s' — skipping email to %s",
            settings.email_provider,
            to_email,
        )


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


def _verification_html(
    customer_name: str,
    date_str: str,
    time_str: str,
    confirm_url: str,
    cancel_url: str | None,
) -> str:
    """HTML email asking the customer to click the confirm link to finalise their hold."""
    cancel_block = ""
    if cancel_url:
        cancel_block = (
            f'<p style="margin:16px 0 0 0; font-size:13px; color:#9ca3af;">'
            f'¿Cambiaste de opinión? '
            f'<a href="{cancel_url}" style="color:#6b7280; text-decoration:underline;">'
            f'Cancelar esta reserva</a></p>'
        )

    expiry_note = (
        f'<p style="margin:24px 0 0 0; font-size:12px; color:#9ca3af; line-height:1.5;">'
        f'Este enlace es v&aacute;lido por <strong>{settings.hold_minutes} minutos</strong>. '
        f'Si expira, simplemente realiza una nueva reserva.</p>'
    )

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

        <table cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px; width:100%; background-color:#ffffff;
                      border-radius:8px; overflow:hidden; border:1px solid #e5e7eb;">

          <!-- Header -->
          <tr>
            <td align="center" bgcolor="#111111"
                style="background-color:#111111; padding:28px 32px;">
              <span style="color:#ffffff; font-size:20px; font-weight:bold; letter-spacing:1px;">
                &#9988; Bailey Barbershop
              </span>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px 40px;">

              <h1 style="margin:0 0 6px 0; font-size:22px; font-weight:bold; color:#111111;">
                Confirma tu cita
              </h1>
              <p style="margin:0 0 28px 0; font-size:14px; color:#6b7280;">
                Tu reserva est&aacute; pendiente. Haz clic en el bot&oacute;n para confirmarla.
              </p>

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
                      <tr>
                        <td style="padding-bottom:14px;">
                          <span style="display:block; font-size:11px; font-weight:bold;
                                       text-transform:uppercase; letter-spacing:0.8px;
                                       color:#9ca3af; margin-bottom:4px;">Fecha</span>
                          <span style="font-size:16px; font-weight:bold; color:#111111;">
                            {date_str}
                          </span>
                        </td>
                      </tr>
                      <tr>
                        <td style="border-top:1px solid #e5e7eb;"></td>
                      </tr>
                      <tr>
                        <td style="padding-top:14px;">
                          <span style="display:block; font-size:11px; font-weight:bold;
                                       text-transform:uppercase; letter-spacing:0.8px;
                                       color:#9ca3af; margin-bottom:4px;">Hora</span>
                          <span style="font-size:16px; font-weight:bold; color:#111111;">
                            {time_str}
                          </span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- Confirm button -->
              <table cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" bgcolor="#111111"
                      style="background-color:#111111; border-radius:6px;">
                    <a href="{confirm_url}"
                       style="display:inline-block; padding:14px 36px; color:#ffffff;
                              font-size:16px; font-weight:bold; text-decoration:none;
                              letter-spacing:0.3px;">
                      Confirmar mi cita
                    </a>
                  </td>
                </tr>
              </table>

              {cancel_block}
              {expiry_note}

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td align="center"
                style="padding:20px 32px; border-top:1px solid #e5e7eb; background-color:#f9fafb;">
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


# ── Public functions ───────────────────────────────────────────────────────────

def send_booking_confirmation_email(
    to_email: str,
    customer_name: str,
    start_time: datetime,
) -> None:
    """Send an appointment confirmation email to the customer."""
    date_str = _format_date_es(start_time)
    time_str = _format_time(start_time)

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
    date_str = _format_date_es(start_time)
    time_str = _format_time(start_time)

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


def send_booking_verification_email(
    to_email: str,
    customer_name: str,
    start_time: datetime,
    confirm_url: str,
    cancel_url: str | None,
) -> None:
    """
    Send the email-verification / hold-confirmation email.
    The customer must click confirm_url to finalise their booking.
    cancel_url is included when the appointment is still within the cancellation window.
    """
    date_str = _format_date_es(start_time)
    time_str = _format_time(start_time)

    subject = f"Confirma tu cita — {date_str} a las {time_str}"

    cancel_line = (
        f"\nSi deseas cancelar: {cancel_url}\n"
        if cancel_url
        else ""
    )

    text_body = (
        f"Hola {customer_name},\n\n"
        f"Tu reserva está pendiente de confirmación. Haz clic en el enlace para confirmarla:\n\n"
        f"  {confirm_url}\n"
        f"{cancel_line}\n"
        f"Este enlace expira en {settings.hold_minutes} minutos.\n\n"
        f"Gracias por tu preferencia,\n"
        f"Bailey Barbershop"
    )

    _send_email(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=_verification_html(customer_name, date_str, time_str, confirm_url, cancel_url),
    )
