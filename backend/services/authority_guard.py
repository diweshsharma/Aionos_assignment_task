"""
Authority guard — deterministic rule checks for escalation triggers.
None of these functions call an LLM; they use keyword matching and numeric
comparisons so the outcome is always reproducible.
"""

from typing import Optional


# ── Legal-threat detection ────────────────────────────────────────────────────

_LEGAL_KEYWORDS = [
    "sue", "lawsuit", "legal action", "legal notice", "lawyer",
    "attorney", "court", "consumer forum", "consumer court",
    "ncdrc", "formal complaint", "file a case", "police complaint",
    "defamation", "social media blast", "going public with this",
    "press release", "media", "news channel",
]


def is_legal_threat(message: str) -> bool:
    """Return True if the message contains a legal-action threat keyword."""
    lower = message.lower()
    return any(kw in lower for kw in _LEGAL_KEYWORDS)


# ── Different-payment-method detection ───────────────────────────────────────

_DIFF_PAYMENT_KEYWORDS = [
    "different card", "another card", "new card",
    "different account", "new account", "another account",
    "different bank", "different payment method",
    "different upi", "another upi",
    "credit card instead", "debit card instead",
    "bank transfer instead", "wallet instead",
    "paytm instead", "gpay instead", "phonepe instead",
    "neft", "imps", "rtgs",
]


def is_different_payment_method(message: str) -> bool:
    """Return True if customer is asking for refund to a different payment method."""
    lower = message.lower()
    return any(kw in lower for kw in _DIFF_PAYMENT_KEYWORDS)


# ── Fare-difference waiver ────────────────────────────────────────────────────

def check_fare_waiver(amount_inr: float, limit_inr: int) -> tuple[bool, str]:
    """
    Returns (within_authority: bool, explanation: str).
    True  → agent can waive this amount.
    False → must escalate to supervisor.
    """
    if amount_inr <= limit_inr:
        return True, (
            f"Fare waiver of ₹{amount_inr:.0f} is within the "
            f"₹{limit_inr} agent authority limit."
        )
    return False, (
        f"Fare waiver of ₹{amount_inr:.0f} exceeds the agent authority "
        f"limit of ₹{limit_inr}. This must be escalated to a supervisor."
    )


# ── Hotel entitlement check ───────────────────────────────────────────────────

def check_hotel_entitlement(
    delay_hours: float,
    entitled_benefits: list[str],
    wants_full_night: bool,
) -> tuple[bool, bool, str]:
    """
    Returns (hotel_allowed: bool, full_night_escalate: bool, explanation: str).

    hotel_allowed      → policy entitles customer to hotel_delayed_hours
    full_night_escalate → customer asked for full night but policy disallows it
    """
    hotel_allowed = "hotel_delayed_hours" in entitled_benefits

    if not hotel_allowed:
        return False, False, (
            f"Policy does not entitle hotel accommodation for a "
            f"{delay_hours:.1f}-hour delay. Hotel is only available for "
            f"delays exceeding 5 hours."
        )

    if wants_full_night:
        return True, True, (
            "Policy covers hotel accommodation for the delayed-hours "
            "portion only — not a full night's stay. A full-night hotel "
            "request must be escalated to a supervisor."
        )

    return True, False, (
        f"Hotel accommodation granted for the {delay_hours:.1f}-hour "
        f"delay period (not a full night)."
    )


# ── Extra-compensation check ──────────────────────────────────────────────────

_UPGRADE_KEYWORDS = [
    "business class", "first class", "business-class", "first-class",
    "upgrade", "premium cabin", "premium economy",
]

_EXTRA_CASH_KEYWORDS = [
    "cash compensation", "extra compensation", "additional compensation",
    "monetary compensation", "damages", "penalty", "punitive",
]


def classify_extra_ask(ask: str) -> Optional[str]:
    """
    Map a free-text extra compensation ask to a category string,
    or return None if it appears to be within normal policy.

    Categories:
      "business_class_upgrade"
      "extra_cash_compensation"
      "full_night_hotel"   (also caught by check_hotel_entitlement, kept for completeness)
      "other_unauthorized"
    """
    lower = ask.lower()
    if any(kw in lower for kw in _UPGRADE_KEYWORDS):
        return "business_class_upgrade"
    if any(kw in lower for kw in _EXTRA_CASH_KEYWORDS):
        return "extra_cash_compensation"
    if "full night" in lower and "hotel" in lower:
        return "full_night_hotel"
    return "other_unauthorized"


def check_extra_compensation(
    extra_asks: list[str],
) -> tuple[bool, list[dict]]:
    """
    Given a list of free-text extra compensation asks from the customer,
    return (has_unauthorized: bool, details: list[dict]).

    Each detail dict: {"ask": str, "category": str, "escalation_reason": str}
    """
    details = []
    for ask in extra_asks:
        category = classify_extra_ask(ask)
        details.append(
            {
                "ask": ask,
                "category": category,
                "escalation_reason": (
                    f"Customer requested '{ask}' which is beyond stated policy "
                    f"and cannot be granted by the agent."
                ),
            }
        )
    return len(details) > 0, details
