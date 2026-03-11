from fastapi.testclient import TestClient

# Base payload reused and overridden per test with dict unpacking.
_CUSTOMER = {
    "full_name": "John Doe",
    "email": "john@example.com",
    "phone": "555-1234",
}


# ── Creation ──────────────────────────────────────────────────────────────────

def test_create_customer_success(client: TestClient):
    response = client.post("/api/v1/customers/", json=_CUSTOMER)
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "John Doe"
    assert data["email"] == "john@example.com"
    assert data["phone"] == "555-1234"
    assert "id" in data


def test_create_customer_duplicate_email_rejected(client: TestClient):
    client.post("/api/v1/customers/", json=_CUSTOMER)
    response = client.post("/api/v1/customers/", json=_CUSTOMER)
    assert response.status_code == 409


def test_create_customer_empty_name_rejected(client: TestClient):
    response = client.post("/api/v1/customers/", json={**_CUSTOMER, "full_name": ""})
    assert response.status_code == 422


def test_create_customer_invalid_email_rejected(client: TestClient):
    response = client.post("/api/v1/customers/", json={**_CUSTOMER, "email": "not-an-email"})
    assert response.status_code == 422


def test_create_customer_phone_too_short_rejected(client: TestClient):
    # Schema requires min_length=7 on phone
    response = client.post("/api/v1/customers/", json={**_CUSTOMER, "phone": "123"})
    assert response.status_code == 422


# ── Retrieval ─────────────────────────────────────────────────────────────────

def test_get_customer_by_id(client: TestClient):
    created = client.post("/api/v1/customers/", json=_CUSTOMER).json()
    response = client.get(f"/api/v1/customers/{created['id']}")
    assert response.status_code == 200
    assert response.json()["email"] == "john@example.com"


def test_get_customer_not_found(client: TestClient):
    response = client.get("/api/v1/customers/999")
    assert response.status_code == 404


def test_list_customers_returns_all(client: TestClient):
    client.post("/api/v1/customers/", json=_CUSTOMER)
    client.post("/api/v1/customers/", json={**_CUSTOMER, "email": "jane@example.com"})
    response = client.get("/api/v1/customers/")
    assert response.status_code == 200
    assert len(response.json()) == 2
