"""Unit tests for booking_service.py"""

import pytest
from datetime import datetime, date

from services.booking_service import (
    get_customer_by_pnr,
    get_customer_by_id,
    create_customer,
    create_booking,
    get_bookings_for_customer,
)
from models import Customer, Booking


def test_get_customer_by_pnr_found(seeded_db):
    db, priya, arvind, meher = seeded_db
    result = get_customer_by_pnr("SK4821X", db)
    assert result is not None
    customer, booking = result
    assert customer.name == "Priya Nair"
    assert booking.status == "CANCELLED"
    assert booking.flight_number == "SK-204"


def test_get_customer_by_pnr_not_found(seeded_db):
    db, *_ = seeded_db
    result = get_customer_by_pnr("INVALID00", db)
    assert result is None


def test_get_customer_by_pnr_prefers_cancelled(seeded_db):
    """When multiple bookings exist for a PNR, CANCELLED is returned first."""
    db, priya, *_ = seeded_db
    # Add a second ON_TIME booking with the same PNR
    db.add(Booking(
        pnr="SK4821X", customer_id=priya.id,
        flight_number="SK-401", route_origin="Goa", route_dest="Delhi",
        flight_date=date(2026, 9, 25), scheduled_departure=datetime(2026, 9, 25, 10, 0),
        actual_departure=None, status="ON_TIME", delay_hours=None,
    ))
    db.commit()
    _, booking = get_customer_by_pnr("SK4821X", db)
    assert booking.status == "CANCELLED"


def test_get_customer_by_id(seeded_db):
    db, priya, *_ = seeded_db
    found = get_customer_by_id(priya.id, db)
    assert found is not None
    assert found.loyalty_tier == "Gold"


def test_create_customer(db):
    data = {
        "name": "Test User",
        "loyalty_tier": "Standard",
        "contact": "test@example.com",
        "flights_last_12mo": 2,
        "prior_complaints": [],
    }
    customer = create_customer(data, db)
    assert customer.id is not None
    assert customer.name == "Test User"
    # Can be retrieved
    found = get_customer_by_id(customer.id, db)
    assert found.name == "Test User"


def test_create_booking(seeded_db):
    db, priya, *_ = seeded_db
    data = {
        "pnr": "NEW001",
        "customer_id": priya.id,
        "flight_number": "SK-999",
        "route_origin": "Mumbai",
        "route_dest": "Chennai",
        "flight_date": date(2026, 10, 1),
        "scheduled_departure": datetime(2026, 10, 1, 9, 0),
        "actual_departure": None,
        "status": "ON_TIME",
        "delay_hours": None,
    }
    booking = create_booking(data, db)
    assert booking.id is not None
    assert booking.pnr == "NEW001"

    # Verifiable via lookup
    result = get_customer_by_pnr("NEW001", db)
    assert result is not None
    _, found_booking = result
    assert found_booking.flight_number == "SK-999"


def test_get_bookings_for_customer(seeded_db):
    db, priya, *_ = seeded_db
    bookings = get_bookings_for_customer(priya.id, db)
    assert len(bookings) >= 1
    assert any(b.pnr == "SK4821X" for b in bookings)
