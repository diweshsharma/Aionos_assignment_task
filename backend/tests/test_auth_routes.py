"""Tests for /auth/token and /auth/lookup-pnr endpoints."""

from config import settings


def test_token_success(client):
    resp = client.post("/auth/token", json={"token": settings.AUTH_TOKEN})
    assert resp.status_code == 200
    assert resp.json()["access_token"] == settings.AUTH_TOKEN


def test_token_invalid(client):
    resp = client.post("/auth/token", json={"token": "invalid_secret"})
    assert resp.status_code == 401


def test_lookup_pnr_success(client):
    resp = client.post("/auth/lookup-pnr", json={"pnr": "SK4821X"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["pnr"] == "SK4821X"
    assert data["name"] == "Priya Nair"
    assert data["loyalty_tier"] == "Gold"
    assert "booking" in data
    assert data["booking"]["status"] == "CANCELLED"


def test_lookup_pnr_not_found(client):
    resp = client.post("/auth/lookup-pnr", json={"pnr": "ZZ0000"})
    assert resp.status_code == 404
    data = resp.json()
    assert "No booking found" in data["detail"]
