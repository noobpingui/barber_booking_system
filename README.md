# Barber Booking System

A backend-focused web application for managing barber shop appointments. Built as a practical portfolio project demonstrating REST API design, business rule enforcement, and a path to cloud deployment.

---

## Problem It Solves

Small barber shops often manage appointments through phone calls, WhatsApp messages, or a physical notebook — all of which are error-prone and hard to track. This system replaces that workflow with:

- An online booking interface where customers can view available slots and book appointments
- A barber-facing dashboard to view and manage the day's schedule at a glance
- Server-side enforcement of business rules such as slot conflicts, cancellation windows, and duplicate bookings

---

## Features

### Customer-facing
- View available 30-minute appointment slots by date
- Book a slot with name, phone number, and email
- Cancel an appointment using email verification (up to 2 hours before the appointment)

### Barber-facing dashboard
- View all appointments for any date
- Navigate between days with prev/next buttons or a date picker
- See confirmed and cancelled counts at a glance
- Cancel any appointment directly from the dashboard

### Business rules enforced
- No double-booking: a confirmed slot blocks any new booking at the same time
- Slot boundary validation: appointments must start on the hour or half-hour
- Business hours: bookings only accepted between 09:00 and 17:30
- No past bookings: start time must be in the future
- Cancellation window: cancellations must be made at least 2 hours in advance
- Email ownership check: customers can only cancel their own appointments
- Duplicate customer prevention: email address must be unique

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.x |
| Database | SQLite (MVP) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Configuration | pydantic-settings |
| Templating | Jinja2 |
| Linting | Ruff |
| Testing | Pytest + HTTPX |
| Target deployment | AWS |

---

## Project Structure

```
barber_booking_system/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, router registration
│   ├── config.py                # Typed settings loaded from .env
│   ├── dependencies.py          # Shared get_db() FastAPI dependency
│   ├── api/v1/
│   │   ├── appointments.py      # Appointment JSON endpoints
│   │   ├── customers.py         # Customer JSON endpoints
│   │   └── dashboard.py        # Barber HTML dashboard routes
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── services/                # Business logic layer
│   ├── db/session.py            # Engine + SessionLocal factory
│   └── templates/               # Jinja2 HTML templates
├── alembic/                     # Database migrations
├── tests/                       # Pytest test suite
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
# Edit .env if needed — defaults work for local SQLite

# 5. Start the server
uvicorn app.main:app --reload
```

The database tables are created automatically on first startup.

| URL | Description |
|---|---|
| `http://localhost:8000/dashboard/` | Barber dashboard |
| `http://localhost:8000/docs` | Interactive API docs (Swagger UI) |
| `http://localhost:8000/redoc` | Alternative API docs |

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
| `POST` | `/api/v1/appointments/` | Book an appointment |
| `GET` | `/api/v1/appointments/` | List all appointments |
| `GET` | `/api/v1/appointments/{id}` | Get appointment by ID |
| `PATCH` | `/api/v1/appointments/{id}/cancel` | Cancel an appointment (requires email) |

### Example: book an appointment

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
| `422` | Validation error (invalid format, past date, outside business hours) |
| `404` | Resource not found |
| `409` | Conflict (slot taken, already cancelled, duplicate email) |
| `403` | Cancellation window has passed |

---

## Configuration

All settings are read from the `.env` file via `pydantic-settings`.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./barber.db` | SQLAlchemy connection string |
| `DEBUG` | `false` | Enable debug mode |
| `CANCELLATION_WINDOW_HOURS` | `2` | Hours before appointment that cancellation is allowed |

---

## Running Tests

```bash
pytest
```

Tests use an in-memory SQLite database isolated per test. No setup required.

---

## Planned Improvements

| Area | Detail |
|---|---|
| **Database** | Migrate to PostgreSQL for production |
| **Authentication** | JWT-based login for the barber dashboard |
| **Email notifications** | Booking confirmation and cancellation emails via SES or SendGrid |
| **Cloud deployment** | AWS deployment with EC2 or ECS, RDS for PostgreSQL, and a load balancer |
| **Customer booking UI** | A simple public-facing page for customers to book without calling the API directly |
| **Week view** | Dashboard view across 7 days for schedule planning |
| **Cancellation history** | Audit log of who cancelled and when |
| **CI/CD pipeline** | GitHub Actions for automated testing and deployment |

---

## Design Decisions

**Why SQLite for MVP?** Eliminates infrastructure setup during early development. SQLAlchemy abstracts the driver, so switching to PostgreSQL requires only a connection string change and a new driver (`psycopg2`).

**Why a services layer?** Route handlers contain no business logic. Services are independently testable and reusable across the JSON API and the HTML dashboard.

**Why Jinja2 templates for the dashboard?** The barber dashboard is a single-user, server-rendered page. A full JavaScript framework would add build complexity with no practical benefit at this stage.

**Why email for cancellation ownership?** Provides a minimal identity check without requiring authentication infrastructure in the MVP phase.
