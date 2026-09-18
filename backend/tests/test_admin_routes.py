"""Tests for /admin/customers, /admin/bookings, and /admin/import endpoints."""

import io

from config import settings


AUTH = {"Authorization": f"Bearer {settings.AUTH_TOKEN}"}


# ── POST /admin/customers ─────────────────────────────────────────────────────

def test_add_customer_success(client):
    resp = client.post(
        "/admin/customers",
        json={
            "name": "Rajiv Sharma",
            "loyalty_tier": "Silver",
            "contact": "rajiv@example.com",
            "flights_last_12mo": 5,
            "prior_complaints": [],
        },
        headers=AUTH,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["name"] == "Rajiv Sharma"
    assert data["loyalty_tier"] == "Silver"


def test_add_customer_invalid_tier(client):
    resp = client.post(
        "/admin/customers",
        json={
            "name": "Bad Tier",
            "loyalty_tier": "Diamond",  # not a valid tier
            "contact": "bad@example.com",
        },
        headers=AUTH,
    )
    assert resp.status_code == 422


def test_add_customer_unauthorized(client):
    resp = client.post(
        "/admin/customers",
        json={"name": "X", "loyalty_tier": "Gold", "contact": "x@x.com"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


# ── POST /admin/bookings ──────────────────────────────────────────────────────

def test_add_booking_success(client):
    # First add a customer to have a valid customer_id
    cust_resp = client.post(
        "/admin/customers",
        json={"name": "Sita Ram", "loyalty_tier": "Gold", "contact": "sita@ex.com"},
        headers=AUTH,
    )
    cust_id = cust_resp.json()["id"]

    resp = client.post(
        "/admin/bookings",
        json={
            "pnr": "TEST001",
            "customer_id": cust_id,
            "flight_number": "SK-900",
            "route_origin": "Chennai",
            "route_dest": "Delhi",
            "flight_date": "2026-11-01",
            "scheduled_departure": "2026-11-01T06:00:00",
            "actual_departure": None,
            "status": "ON_TIME",
            "delay_hours": None,
        },
        headers=AUTH,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["pnr"] == "TEST001"
    assert data["flight_number"] == "SK-900"


def test_add_booking_invalid_status(client):
    resp = client.post(
        "/admin/bookings",
        json={
            "pnr": "BAD001",
            "customer_id": 1,
            "flight_number": "SK-001",
            "route_origin": "A", "route_dest": "B",
            "flight_date": "2026-11-01",
            "scheduled_departure": "2026-11-01T06:00:00",
            "status": "UNKNOWN_STATUS",
        },
        headers=AUTH,
    )
    assert resp.status_code == 422


# ── POST /admin/import ────────────────────────────────────────────────────────

def test_import_customers_csv_success(client):
    csv_content = (
        "name,loyalty_tier,contact,flights_last_12mo,prior_complaints\n"
        "Vikram Bose,Gold,vikram@example.com,8,[]\n"
        "Prerna Singh,Silver,prerna@example.com,2,[]\n"
    )
    resp = client.post(
        "/admin/import",
        headers=AUTH,
        files={"customers_csv": ("customers.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["customers"]["status"] == "success"
    assert data["customers"]["success_count"] == 2


def test_import_customers_csv_rejects_malformed_row(client):
    """A single bad row must cause the entire file to be rejected."""
    csv_content = (
        "name,loyalty_tier,contact,flights_last_12mo,prior_complaints\n"
        "Good User,Gold,good@example.com,3,[]\n"
        "Bad User,INVALID_TIER,bad@example.com,1,[]\n"  # invalid tier
    )
    resp = client.post(
        "/admin/import",
        headers=AUTH,
        files={"customers_csv": ("c.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["customers"]["status"] == "rejected"
    assert data["customers"]["success_count"] == 0
    assert len(data["customers"]["failures"]) >= 1


def test_import_no_files_raises_422(client):
    resp = client.post("/admin/import", headers=AUTH)
    assert resp.status_code == 422


def test_import_bookings_csv_success(client):
    # Seed a customer first
    cust_resp = client.post(
        "/admin/customers",
        json={"name": "CSV Test", "loyalty_tier": "Standard", "contact": "csv@test.com"},
        headers=AUTH,
    )
    cust_id = cust_resp.json()["id"]

    csv_content = (
        "pnr,customer_id,flight_number,route_origin,route_dest,"
        "flight_date,scheduled_departure,actual_departure,status,delay_hours\n"
        f"CSVB01,{cust_id},SK-500,Mumbai,Pune,2026-12-01,"
        "2026-12-01T07:00:00,,ON_TIME,\n"
    )
    resp = client.post(
        "/admin/import",
        headers=AUTH,
        files={"bookings_csv": ("bookings.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["bookings"]["status"] == "success"
    assert data["bookings"]["success_count"] == 1
