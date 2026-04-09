# Barber Booking System

A full-stack web application for managing barber shop appointments. Built as a portfolio project demonstrating REST API design, business rule enforcement, authentication, email notifications, and AWS cloud deployment.

---

## Problem It Solves

Small barber shops often manage appointments through phone calls, WhatsApp messages, or a physical notebook — all of which are error-prone and hard to track. This system replaces that workflow with:

- An online booking interface where customers can view available slots and book appointments
- An email verification flow that confirms the booking and delivers a cancellation link
- A barber-facing dashboard to view and manage the schedule at a glance
- Server-side enforcement of business rules such as slot conflicts, cancellation windows, and duplicate bookings

---

## Features

### Customer-facing
- View available 30-minute appointment slots by date
- Book a slot with name, phone number, and email
- Receive a verification email and confirm the booking via a time-limited link
- Cancel an appointment using a token-based link sent by email

### Barber-facing dashboard (requires login)
- View all appointments for any date
- Navigate between days with prev/next buttons or a date picker
- See confirmed, cancelled, and blocked slot counts at a glance
- Cancel any appointment directly from the dashboard
- Block and unblock specific time slots to mark unavailability

### Business rules enforced
- **Hold system**: booking creates a 10-minute hold; slot is only confirmed after email verification
- **One booking per window**: each customer may have at most one appointment within any 7-day rolling window
- **No double-booking**: confirmed appointments and active holds block the same slot
- **Slot boundary validation**: appointments must start on the hour or half-hour
- **Business hours**: bookings only accepted between 09:00 and 20:30
- **Lead time**: bookings must be made at least 30 minutes in advance
- **Cancellation window**: cancellations only allowed up to the configured cutoff (default: 1 hour before)
- **Token-based ownership**: cancellation requires the unique link sent to the customer's email
- **Duplicate customer prevention**: email address must be unique

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.x |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Configuration | pydantic-settings |
| Templating | Jinja2 + Bootstrap 5 |
| Authentication | JWT (PyJWT) + bcrypt |
| Email | Resend API or AWS SES |
| Linting | Ruff |
| Testing | Pytest + HTTPX |
| Deployment | AWS EC2 + Nginx + Gunicorn + systemd |
| CI/CD | GitHub Actions |

---

## Project Structure

```
barber_booking_system/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, router registration
│   ├── config.py                # Typed settings loaded from .env
│   ├── dependencies.py          # get_db(), auth dependencies (cookie + Bearer)
│   ├── api/v1/
│   │   ├── auth.py              # Login / logout HTML routes
│   │   ├── booking.py           # Customer booking flow HTML routes
│   │   ├── dashboard.py         # Barber dashboard HTML routes
│   │   ├── appointments.py      # Appointment JSON API endpoints
│   │   └── customers.py         # Customer JSON API endpoints
│   ├── core/
│   │   ├── security.py          # bcrypt hashing, JWT creation/decoding
│   │   └── tokens.py            # Secure random token generation + SHA-256 hashing
│   ├── models/
│   │   ├── base.py              # DeclarativeBase
│   │   ├── user.py              # Barber user (email + password_hash)
│   │   ├── customer.py          # Customer
│   │   ├── appointment.py       # Appointment (hold → confirmed → cancelled/expired)
│   │   └── blocked_slot.py      # Manually blocked time slots
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── services/
│   │   ├── appointment_service.py   # Slot logic, holds, tokens, cancellation
│   │   ├── customer_service.py      # Customer CRUD
│   │   ├── notification_service.py  # Email sending (Resend / AWS SES)
│   │   └── user_service.py          # User lookup
│   ├── db/session.py            # Engine + SessionLocal factory
│   └── templates/               # Jinja2 HTML templates (Bootstrap 5, vintage theme)
├── alembic/                     # Database migrations
├── deploy/
│   ├── barber.service           # systemd service unit
│   ├── nginx.conf               # Nginx reverse proxy config
│   └── deploy.sh                # EC2 deployment script
├── scripts/
│   └── create_barber.py         # CLI script to create a barber user
├── tests/                       # Pytest test suite
├── assets/
│   └── barbershop.ico           # Favicon
├── gunicorn.conf.py             # Production WSGI config
├── .env.example
├── alembic.ini
└── pyproject.toml
```

---

## Local Setup

### Prerequisites
- Python 3.11+
- pip

### Steps

```bash
# 1. Clone the repository
git clone <repo-url>
cd barber_booking_system

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/Scripts/activate   # Windows
source .venv/bin/activate       # macOS / Linux

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY for JWT signing
# Set EMAIL_PROVIDER and credentials if you want email sending

# 5. Start the server
uvicorn app.main:app --reload
```

Tables are created automatically on first startup.

```bash
# 6. Create a barber account (one-time)
python scripts/create_barber.py --email barber@example.com --password secret
```

| URL | Description |
|---|---|
| `http://localhost:8000/` | Redirects to dashboard (login required) |
| `http://localhost:8000/login` | Barber login page |
| `http://localhost:8000/dashboard/` | Barber dashboard |
| `http://localhost:8000/booking/` | Customer booking form |
| `http://localhost:8000/docs` | Interactive API docs (Swagger UI) |
| `http://localhost:8000/redoc` | Alternative API docs |

---

## Booking Flow

```
Customer fills form
      │
      ▼
Hold created (10 min expiry)  ──── slot blocked for other customers
      │
      ▼
Verification email sent
      │
Customer clicks confirm link
      │
      ▼
Appointment confirmed  ──── confirmation email + cancellation link sent
      │
      ▼ (optional)
Customer clicks cancel link
      │
      ▼
Appointment cancelled  ──── cancellation email sent
```

---

## API Overview

### Customers

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/customers/` | Register a new customer |
| `GET` | `/api/v1/customers/` | List all customers |
| `GET` | `/api/v1/customers/{id}` | Get customer by ID |

### Appointments

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/appointments/available-slots?target_date=YYYY-MM-DD` | List available slots for a date |
| `POST` | `/api/v1/appointments/` | Book an appointment (direct confirm, JSON API) |
| `GET` | `/api/v1/appointments/` | List all appointments |
| `GET` | `/api/v1/appointments/{id}` | Get appointment by ID |
| `PATCH` | `/api/v1/appointments/{id}/cancel` | Cancel an appointment (requires email) |

### Example: book via the JSON API

```bash
# 1. Create a customer
curl -X POST http://localhost:8000/api/v1/customers/ \
  -H "Content-Type: application/json" \
  -d '{"full_name": "John Doe", "email": "john@example.com", "phone": "555-1234"}'

# 2. Check available slots
curl "http://localhost:8000/api/v1/appointments/available-slots?target_date=2026-06-01"

# 3. Book a slot
curl -X POST http://localhost:8000/api/v1/appointments/ \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 1, "start_time": "2026-06-01T10:00:00"}'

# 4. Cancel (requires matching email)
curl -X PATCH http://localhost:8000/api/v1/appointments/1/cancel \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com"}'
```

### Error responses

| Status | Meaning |
|---|---|
| `401` | Not authenticated (dashboard/protected routes) |
| `403` | Cancellation window has passed |
| `404` | Resource not found |
| `409` | Conflict (slot taken, already cancelled, duplicate email) |
| `422` | Validation error (invalid format, past date, outside business hours) |

---

## Configuration

All settings are read from the `.env` file via `pydantic-settings`.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./barber.db` | SQLAlchemy connection string |
| `DEBUG` | `false` | Enable debug mode |
| `SECRET_KEY` | `change-me` | JWT signing key — **must be changed in production** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | JWT token lifetime (8 hours) |
| `CANCELLATION_WINDOW_HOURS` | `1` | Hours before appointment that cancellation closes |
| `HOLD_MINUTES` | `10` | Minutes an unconfirmed hold is valid |
| `EMAIL_PROVIDER` | — | `resend` or `ses` (leave unset to disable email) |
| `EMAIL_FROM` | — | Sender address for notifications |
| `RESEND_API_KEY` | — | API key for Resend (if `EMAIL_PROVIDER=resend`) |
| `AWS_ACCESS_KEY_ID` | — | AWS credentials (if `EMAIL_PROVIDER=ses`) |
| `AWS_SECRET_ACCESS_KEY` | — | AWS credentials (if `EMAIL_PROVIDER=ses`) |
| `AWS_REGION` | — | AWS region (if `EMAIL_PROVIDER=ses`) |

---

## Running Tests

```bash
pytest
```

Tests use an in-memory SQLite database isolated per test. No external services required.

---

## Deployment (AWS EC2)

The `deploy/` directory contains production configuration files:

- **`barber.service`** — systemd unit that runs Gunicorn and auto-restarts on crash
- **`nginx.conf`** — Nginx reverse proxy (HTTP; add Certbot for HTTPS)
- **`deploy.sh`** — pulls latest `main`, installs deps, runs `alembic upgrade head`, restarts service

The GitHub Actions workflow (`.github/workflows/deploy.yml`) SSHs into the EC2 instance and runs `deploy.sh` on every push to `main`.

---

## Design Decisions

**Why SQLite for development?** Eliminates infrastructure setup during early development. SQLAlchemy abstracts the driver, so switching to PostgreSQL requires only a connection string change and the `psycopg2-binary` driver.

**Why a services layer?** Route handlers contain no business logic. Services are independently testable and reusable across the JSON API and the HTML routes.

**Why Jinja2 templates?** The barber dashboard and booking form are server-rendered pages. A JavaScript framework would add build complexity with no practical benefit at this scale.

**Why a hold system instead of direct confirm?** Prevents ghost bookings from customers who never complete their details. The 10-minute hold expires automatically, releasing the slot back to other customers.

**Why token-based cancellation?** Provides secure, authenticated cancellation without requiring customers to register or log in. Each cancellation link is single-use and tied to a specific appointment.
