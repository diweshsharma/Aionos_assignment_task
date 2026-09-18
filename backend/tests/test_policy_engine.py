"""Unit tests for policy_engine.py — verifies YAML-driven rule evaluation."""

import pytest


def test_delay_benefits_under_3h(policy):
    benefits = policy.get_delay_benefits(2.0)
    assert benefits == ["meal_voucher_500"]


def test_delay_benefits_exactly_3h(policy):
    """3.0h is NOT < 3 so it falls into the second tier (voucher + lounge)."""
    benefits = policy.get_delay_benefits(3.0)
    assert "meal_voucher_500" in benefits
    assert "lounge_access" in benefits
    assert "hotel_delayed_hours" not in benefits


def test_delay_benefits_between_3_and_5(policy):
    benefits = policy.get_delay_benefits(4.0)
    assert "meal_voucher_500" in benefits
    assert "lounge_access" in benefits
    assert "hotel_delayed_hours" not in benefits


def test_delay_benefits_exactly_5h(policy):
    """5.0h is NOT < 5 so it falls into the null tier (all three benefits)."""
    benefits = policy.get_delay_benefits(5.0)
    assert "meal_voucher_500" in benefits
    assert "lounge_access" in benefits
    assert "hotel_delayed_hours" in benefits


def test_delay_benefits_over_5h(policy):
    benefits = policy.get_delay_benefits(6.0)
    assert "meal_voucher_500" in benefits
    assert "lounge_access" in benefits
    assert "hotel_delayed_hours" in benefits


def test_cancellation_policy(policy):
    cp = policy.get_cancellation_policy()
    assert cp["rebook_window_hours"] == 24
    assert cp["refund_processing_days"] == 7
    assert cp["refund_to_original_payment_only"] is True


def test_fare_waiver_limit(policy):
    assert policy.get_fare_waiver_limit() == 1500


def test_refund_policy(policy):
    rp = policy.get_refund_policy()
    assert rp["processing_days"] == 7
    assert rp["original_payment_only"] is True


def test_priority_tiers(policy):
    assert policy.is_priority_tier("Gold") is True
    assert policy.is_priority_tier("Platinum") is True
    assert policy.is_priority_tier("Silver") is False
    assert policy.is_priority_tier("Standard") is False


def test_generate_policy_documents(policy):
    docs = policy.generate_policy_documents()
    assert len(docs) >= 5
    # Each doc must be a non-empty string
    for doc in docs:
        assert isinstance(doc, str) and len(doc) > 50
    # Check key content
    full_text = " ".join(docs)
    assert "1500" in full_text       # fare waiver limit from YAML
    assert "24" in full_text         # rebook window hours
    assert "7" in full_text          # refund processing days
    assert "hotel" in full_text.lower()
    assert "escalat" in full_text.lower()


def test_policy_loads_from_yaml(policy):
    """Raw policy dict should have all expected top-level keys."""
    raw = policy.raw
    assert "delay_tiers" in raw
    assert "fare_waiver_limit_inr" in raw
    assert "cancellation_rebook_window_hours" in raw
    assert "refund_processing_days" in raw
    assert "loyalty_priority_tiers" in raw


def test_delay_tiers_consistent_with_spec(policy):
    """The YAML tiers must match the exact spec thresholds."""
    tiers = policy.raw["delay_tiers"]
    # Tier 0: < 3h
    assert tiers[0]["max_hours"] == 3
    # Tier 1: 3–5h
    assert tiers[1]["max_hours"] == 5
    # Tier 2: > 5h (no upper bound)
    assert tiers[2]["max_hours"] is None
