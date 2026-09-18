"""
Policy engine — loads policy_rules.yaml at startup and exposes deterministic
accessor methods.  No thresholds are hardcoded in Python; every number
comes from the YAML file so policy changes are config-only edits.
"""

from pathlib import Path
from typing import Optional
import yaml

from config import settings


class PolicyEngine:
    """Singleton-style wrapper around policy_rules.yaml."""

    def __init__(self, yaml_path: Optional[str] = None) -> None:
        self._yaml_path = Path(yaml_path or settings.POLICY_YAML_PATH)
        self._policy: dict = {}
        self.load()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def load(self) -> None:
        """(Re-)load policy from YAML. Safe to call at runtime."""
        with open(self._yaml_path, "r", encoding="utf-8") as fh:
            self._policy = yaml.safe_load(fh)

    @property
    def raw(self) -> dict:
        return self._policy

    # ── Delay compensation ────────────────────────────────────────────────────

    def get_delay_benefits(self, delay_hours: float) -> list[str]:
        """
        Return the benefit list for the given delay duration.

        Tiers are evaluated in YAML order; the first tier whose
        max_hours > delay_hours (or whose max_hours is null) wins.
        """
        for tier in self._policy["delay_tiers"]:
            max_h = tier["max_hours"]
            if max_h is None or delay_hours < max_h:
                return list(tier["benefits"])
        return []

    # ── Cancellation ─────────────────────────────────────────────────────────

    def get_cancellation_policy(self) -> dict:
        return {
            "rebook_window_hours": self._policy["cancellation_rebook_window_hours"],
            "refund_processing_days": self._policy["refund_processing_days"],
            "refund_to_original_payment_only": True,
        }

    # ── Fare-difference waiver ────────────────────────────────────────────────

    def get_fare_waiver_limit(self) -> int:
        return int(self._policy["fare_waiver_limit_inr"])

    # ── Refund ────────────────────────────────────────────────────────────────

    def get_refund_policy(self) -> dict:
        return {
            "processing_days": self._policy["refund_processing_days"],
            "original_payment_only": True,
        }

    # ── Loyalty ───────────────────────────────────────────────────────────────

    def is_priority_tier(self, loyalty_tier: str) -> bool:
        return loyalty_tier in self._policy["loyalty_priority_tiers"]

    def get_priority_tiers(self) -> list[str]:
        return list(self._policy["loyalty_priority_tiers"])

    # ── Human-readable text for RAG indexing ─────────────────────────────────

    def generate_policy_documents(self) -> list[str]:
        """
        Convert the loaded policy to a list of plain-English paragraphs
        suitable for chunking into Chroma.  Call this whenever the YAML
        is (re-)loaded so Chroma always mirrors the YAML.
        """
        p = self._policy
        docs: list[str] = []

        # Cancellation
        docs.append(
            f"Flight Cancellation Policy: When a flight is cancelled due to airline "
            f"operations, customers have two options: (1) a free rebook on the next "
            f"available flight departing within {p['cancellation_rebook_window_hours']} "
            f"hours of the original departure time, or (2) a full refund to the original "
            f"payment method within {p['refund_processing_days']} business days. "
            f"Refunds are processed to the original payment method only — no exceptions. "
            f"Requesting a refund to a different payment method must be escalated."
        )

        # Delay tiers
        tiers = p["delay_tiers"]
        for i, tier in enumerate(tiers):
            max_h = tier["max_hours"]
            prev_max = tiers[i - 1]["max_hours"] if i > 0 else None

            if i == 0:
                range_desc = f"less than {max_h} hours"
            elif max_h is None:
                range_desc = f"more than {prev_max} hours"
            else:
                range_desc = f"between {prev_max} and {max_h} hours"

            benefit_names = {
                "meal_voucher_500": "a ₹500 meal voucher",
                "lounge_access": "lounge access",
                "hotel_delayed_hours": (
                    "hotel accommodation for the delayed-hours portion only "
                    "(NOT a full night — full-night hotel requests must be escalated)"
                ),
            }
            benefits_str = ", ".join(
                benefit_names.get(b, b) for b in tier["benefits"]
            )
            docs.append(
                f"Flight Delay Policy — Delays {range_desc}: "
                f"Passengers are entitled to: {benefits_str}."
            )

        # Fare waiver
        docs.append(
            f"Voluntary Rebook Fare Difference Policy: When a customer voluntarily rebooks "
            f"to a higher-fare flight (not caused by the airline), the customer pays the "
            f"fare difference. Agents may waive up to ₹{p['fare_waiver_limit_inr']} without "
            f"supervisor approval. Any waiver request above ₹{p['fare_waiver_limit_inr']} "
            f"must be escalated to a supervisor and cannot be granted by the agent."
        )

        # Loyalty
        tiers_str = " and ".join(p["loyalty_priority_tiers"])
        docs.append(
            f"Loyalty Tier Priority Policy: {tiers_str} tier members receive priority "
            f"rebooking queue placement. No additional monetary compensation beyond the "
            f"standard policy is granted solely on the basis of loyalty tier."
        )

        # Escalation triggers
        docs.append(
            f"Escalation Policy — the following situations MUST be escalated to a human "
            f"supervisor and cannot be resolved by the automated agent: "
            f"(1) any compensation request beyond what the stated policy allows "
            f"(e.g., business-class upgrades, extra cash payments); "
            f"(2) fare-difference waivers above ₹{p['fare_waiver_limit_inr']}; "
            f"(3) full-night hotel requests (policy only covers the delayed-hours portion); "
            f"(4) non-airline-caused exception requests; "
            f"(5) legal action threats or formal complaint threats — escalate immediately, "
            f"mid-conversation, regardless of any other topic being discussed; "
            f"(6) refund requests to a different payment method than the original."
        )

        return docs


# Module-level singleton — imported by other services and agent nodes.
policy_engine = PolicyEngine()
