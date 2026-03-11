from fastapi.testclient import TestClient

# Far-future dates so the "must be in the future" validator never fails in CI.
FUTURE_SLOT   = "2030-06-01T10:00:00"   # valid — 10:00, within business hours
FUTURE_SLOT_2 = "2030-06-01T10:30:00"   # valid — 10:30, adjacent slot
PAST_SLOT     = "2020-01-01T10:00:00"   # invalid — in the past
INVALID_BOUNDARY = "2030-06-01T10:15:00"  # invalid — not on :00 or :30
BEFORE_HOURS  = "2030-06-01T07:00:00"   # invalid — before 09:00
AFTER_HOURS   = "2030-06-01T21:30:00"   # invalid — after 20:30

_CUSTOMER_A = {"full_name": "Jane Doe",  "email": "jane@example.com", "phone": "555-5678"}
_CUSTOMER_B = {"full_name": "Bob Smith", "email": "bob@example.com",  "phone": "555-9999"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_customer(client: TestClient, payload: dict = _CUSTOMER_A) -> dict:
    return client.post("/api/v1/customers/", json=payload).json()


def _book(client: TestClient, customer_id: int, start_time: str):
    return client.post("/api/v1/appointments/", json={
        "customer_id": customer_id,
        "start_time": start_time,
    })


def _cancel(client: TestClient, appointment_id: int, email: str = _CUSTOMER_A["email"]):
    return client.patch(
        f"/api/v1/appointments/{appointment_id}/cancel",
        json={"email": email},
    )


# ── Booking creation ──────────────────────────────────────────────────────────

def test_book_success(client: TestClient):
    customer = _make_customer(client)
    response = _book(client, customer["id"], FUTURE_SLOT)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "confirmed"
    assert data["customer_id"] == customer["id"]
    assert "id" in data
    assert "start_time" in data


def test_book_unknown_customer_returns_404(client: TestClient):
    response = _book(client, customer_id=999, start_time=FUTURE_SLOT)
    assert response.status_code == 404


def test_book_past_slot_returns_422(client: TestClient):
    customer = _make_customer(client)
    response = _book(client, customer["id"], PAST_SLOT)
    assert response.status_code == 422


def test_book_invalid_boundary_returns_422(client: TestClient):
    customer = _make_customer(client)
    response = _book(client, customer["id"], INVALID_BOUNDARY)
    assert response.status_code == 422


def test_book_before_business_hours_returns_422(client: TestClient):
    customer = _make_customer(client)
    response = _book(client, customer["id"], BEFORE_HOURS)
    assert response.status_code == 422


def test_book_after_business_hours_returns_422(client: TestClient):
    customer = _make_customer(client)
    response = _book(client, customer["id"], AFTER_HOURS)
    assert response.status_code == 422


# ── Conflict prevention ───────────────────────────────────────────────────────

def test_duplicate_slot_same_customer_returns_409(client: TestClient):
    customer = _make_customer(client)
    _book(client, customer["id"], FUTURE_SLOT)
    response = _book(client, customer["id"], FUTURE_SLOT)
    assert response.status_code == 409


def test_duplicate_slot_different_customers_returns_409(client: TestClient):
    """The slot is global — a second customer cannot take an already-booked time."""
    customer_a = _make_customer(client, _CUSTOMER_A)
    customer_b = _make_customer(client, _CUSTOMER_B)
    _book(client, customer_a["id"], FUTURE_SLOT)
    response = _book(client, customer_b["id"], FUTURE_SLOT)
    assert response.status_code == 409


def test_adjacent_slots_are_independent(client: TestClient):
    """Booking 10:00 must not block 10:30 for a different customer."""
    customer_a = _make_customer(client, _CUSTOMER_A)
    customer_b = _make_customer(client, _CUSTOMER_B)
    _book(client, customer_a["id"], FUTURE_SLOT)
    response = _book(client, customer_b["id"], FUTURE_SLOT_2)
    assert response.status_code == 201


def test_cancelled_slot_becomes_bookable_again(client: TestClient):
    """After a cancellation the freed slot must accept a new booking."""
    customer = _make_customer(client)
    appt = _book(client, customer["id"], FUTURE_SLOT).json()
    _cancel(client, appt["id"])
    response = _book(client, customer["id"], FUTURE_SLOT)
    assert response.status_code == 201


# ── Cancellation ──────────────────────────────────────────────────────────────

def test_cancel_success(client: TestClient):
    customer = _make_customer(client)
    appt = _book(client, customer["id"], FUTURE_SLOT).json()
    response = _cancel(client, appt["id"])
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cancel_wrong_email_returns_404(client: TestClient):
    """Wrong email must return 404, not reveal that the appointment exists."""
    customer = _make_customer(client)
    appt = _book(client, customer["id"], FUTURE_SLOT).json()
    response = _cancel(client, appt["id"], email="impostor@example.com")
    assert response.status_code == 404


def test_cancel_nonexistent_appointment_returns_404(client: TestClient):
    response = _cancel(client, appointment_id=999)
    assert response.status_code == 404


def test_cancel_already_cancelled_returns_409(client: TestClient):
    customer = _make_customer(client)
    appt = _book(client, customer["id"], FUTURE_SLOT).json()
    _cancel(client, appt["id"])
    response = _cancel(client, appt["id"])
    assert response.status_code == 409


def test_cancel_missing_email_body_returns_422(client: TestClient):
    """The cancel endpoint must reject requests with no body."""
    customer = _make_customer(client)
    appt = _book(client, customer["id"], FUTURE_SLOT).json()
    response = client.patch(f"/api/v1/appointments/{appt['id']}/cancel")
    assert response.status_code == 422


# ── One-per-window rule (enforced in HTML booking flow, not the raw API) ───────

def test_same_customer_can_rebook_same_week_via_api_after_cancel(client: TestClient):
    """Raw API has no week-limit; after cancellation the slot is free again."""
    customer = _make_customer(client)
    appt = _book(client, customer["id"], FUTURE_SLOT).json()
    _cancel(client, appt["id"])
    response = _book(client, customer["id"], FUTURE_SLOT_2)
    assert response.status_code == 201


# ── Available slots ───────────────────────────────────────────────────────────

def test_available_slots_full_day(client: TestClient):
    """An empty day must return all 24 slots (09:00–20:30 in 30-min steps)."""
    response = client.get("/api/v1/appointments/available-slots?target_date=2030-06-01")
    assert response.status_code == 200
    slots = response.json()
    assert len(slots) == 24
    assert all("start_time" in s for s in slots)


def test_available_slots_excludes_booked(client: TestClient):
    customer = _make_customer(client)
    _book(client, customer["id"], FUTURE_SLOT)   # books 10:00
    response = client.get("/api/v1/appointments/available-slots?target_date=2030-06-01")
    slot_times = [s["start_time"] for s in response.json()]
    assert not any("T10:00:00" in t for t in slot_times)
    assert len(slot_times) == 23


def test_available_slots_restored_after_cancel(client: TestClient):
    """A cancelled slot must reappear in the available list."""
    customer = _make_customer(client)
    appt = _book(client, customer["id"], FUTURE_SLOT).json()
    _cancel(client, appt["id"])
    response = client.get("/api/v1/appointments/available-slots?target_date=2030-06-01")
    slot_times = [s["start_time"] for s in response.json()]
    assert any("T10:00:00" in t for t in slot_times)
    assert len(slot_times) == 24


def test_available_slots_past_date_returns_empty(client: TestClient):
    response = client.get("/api/v1/appointments/available-slots?target_date=2020-01-01")
    assert response.status_code == 200
    assert response.json() == []


def test_available_slots_missing_date_returns_422(client: TestClient):
    """The date parameter is required."""
    response = client.get("/api/v1/appointments/available-slots")
    assert response.status_code == 422
