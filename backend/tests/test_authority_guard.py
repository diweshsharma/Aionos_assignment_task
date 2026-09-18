"""Unit tests for authority_guard.py"""

import pytest

from services.authority_guard import (
    is_legal_threat,
    is_different_payment_method,
    check_fare_waiver,
    check_hotel_entitlement,
    check_extra_compensation,
    classify_extra_ask,
)


# ── Legal threat detection ────────────────────────────────────────────────────

@pytest.mark.parametrize("msg", [
    "I will sue you",
    "I'm taking legal action",
    "My lawyer will be in touch",
    "I'll file a case in consumer court",
    "I'm going to consumer forum",
    "Legal notice incoming",
])
def test_is_legal_threat_true(msg):
    assert is_legal_threat(msg) is True


@pytest.mark.parametrize("msg", [
    "I want a refund",
    "Please rebook my flight",
    "I need a hotel room",
    "My flight is delayed 4 hours",
])
def test_is_legal_threat_false(msg):
    assert is_legal_threat(msg) is False


# ── Different payment method ──────────────────────────────────────────────────

@pytest.mark.parametrize("msg", [
    "Please refund to a different card",
    "Send it to my bank transfer instead",
    "Use my Paytm instead",
    "Refund to another account",
])
def test_different_payment_true(msg):
    assert is_different_payment_method(msg) is True


def test_different_payment_false():
    assert is_different_payment_method("I want a refund to my original card") is False


# ── Fare waiver ───────────────────────────────────────────────────────────────

def test_fare_waiver_within_limit():
    ok, msg = check_fare_waiver(1000.0, 1500)
    assert ok is True
    assert "within" in msg.lower()


def test_fare_waiver_at_limit():
    ok, _ = check_fare_waiver(1500.0, 1500)
    assert ok is True


def test_fare_waiver_exceeds_limit():
    ok, msg = check_fare_waiver(2000.0, 1500)
    assert ok is False
    assert "escalated" in msg.lower()


def test_fare_waiver_just_over_limit():
    ok, _ = check_fare_waiver(1501.0, 1500)
    assert ok is False


# ── Hotel entitlement ─────────────────────────────────────────────────────────

def test_hotel_not_entitled_short_delay():
    ok, full_night_esc, explanation = check_hotel_entitlement(
        delay_hours=4.0,
        entitled_benefits=["meal_voucher_500", "lounge_access"],
        wants_full_night=False,
    )
    assert ok is False
    assert full_night_esc is False
    assert "not entitle" in explanation.lower() or "5 hours" in explanation.lower()


def test_hotel_entitled_delayed_hours_only():
    ok, full_night_esc, _ = check_hotel_entitlement(
        delay_hours=6.0,
        entitled_benefits=["meal_voucher_500", "lounge_access", "hotel_delayed_hours"],
        wants_full_night=False,
    )
    assert ok is True
    assert full_night_esc is False


def test_hotel_entitled_but_full_night_requested():
    ok, full_night_esc, explanation = check_hotel_entitlement(
        delay_hours=6.0,
        entitled_benefits=["meal_voucher_500", "lounge_access", "hotel_delayed_hours"],
        wants_full_night=True,
    )
    assert ok is True           # hotel IS granted (for delayed hours)
    assert full_night_esc is True   # but full-night request needs escalation
    assert "full" in explanation.lower()


# ── Extra compensation ────────────────────────────────────────────────────────

def test_business_class_upgrade_classified():
    cat = classify_extra_ask("Free business class upgrade")
    assert cat == "business_class_upgrade"


def test_extra_cash_classified():
    cat = classify_extra_ask("₹3000 cash compensation for the trouble")
    assert cat == "extra_cash_compensation"


def test_check_extra_compensation_detects_upgrade():
    has_unauth, details = check_extra_compensation(
        ["free business class upgrade", "lounge access"]
    )
    assert has_unauth is True
    cats = [d["category"] for d in details]
    assert "business_class_upgrade" in cats


def test_check_extra_compensation_empty():
    has_unauth, details = check_extra_compensation([])
    assert has_unauth is False
    assert details == []
