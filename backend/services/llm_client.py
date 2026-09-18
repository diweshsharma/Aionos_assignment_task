"""
LLM client — wraps Groq (primary + fallback model) and an optional
external OpenAI-compatible endpoint as a final fallback.

The mock class at the bottom is used in tests without any network calls.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Intent extraction result structure ───────────────────────────────────────

def _default_intents() -> dict:
    return {
        "primary_intent": "info",
        "wants_refund": False,
        "wants_rebook": False,
        "wants_hotel": False,
        "wants_full_night_hotel": False,
        "extra_compensation_asks": [],
        "fare_difference_waiver_inr": None,
        "wants_different_payment_method": False,
        "is_legal_threat": False,
    }


_INTENT_SYSTEM_PROMPT = """\
You are an intent extraction assistant for an airline customer support system.
Extract the customer's intent from their message and return a JSON object with EXACTLY these fields:

{
  "primary_intent": "<refund|rebook|info|compensation|complaint>",
  "wants_refund": <true|false>,
  "wants_rebook": <true|false>,
  "wants_hotel": <true|false>,
  "wants_full_night_hotel": <true|false>,
  "extra_compensation_asks": ["list of strings — any demands BEYOND standard policy, e.g. 'free business class upgrade', '₹3000 cash compensation'"],
  "fare_difference_waiver_inr": <number or null — the INR amount the customer wants waived for a higher-fare rebook>,
  "wants_different_payment_method": <true|false — true if they want refund to a different card/account>,
  "is_legal_threat": <true|false — true if they mention lawsuit, legal notice, consumer court, etc.>
}

Rules:
- extra_compensation_asks MUST only contain asks that go BEYOND the airline's standard delay/cancellation policy.
- Standard asks (refund to original payment, rebook on next flight, meal voucher, lounge, hotel for delays) are NOT extra compensation.
- Return only valid JSON, no commentary.\
"""


class LLMClient:
    """Production LLM client with Groq primary + fallback chain."""

    def __init__(self) -> None:
        from config import settings
        self._settings = settings
        self._groq_client = None

    @property
    def _groq(self):
        if self._groq_client is None:
            from groq import Groq
            self._groq_client = Groq(api_key=self._settings.GROQ_API_KEY)
        return self._groq_client

    # ── Intent extraction ─────────────────────────────────────────────────────

    def extract_intents(self, message: str) -> dict:
        """Use LLM to extract structured intents.  Falls back through model chain."""
        messages = [
            {"role": "system", "content": _INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]
        for model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
            try:
                resp = self._groq.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                raw = resp.choices[0].message.content
                parsed = json.loads(raw)
                return {**_default_intents(), **parsed}
            except Exception as exc:
                logger.warning("Groq model %s failed intent extraction: %s", model, exc)

        # Keyword-based last resort (never touches LLM)
        return self._keyword_intents(message)

    def _keyword_intents(self, message: str) -> dict:
        lower = message.lower()
        result = _default_intents()
        result["wants_refund"] = "refund" in lower
        result["wants_rebook"] = any(
            w in lower for w in ["rebook", "reschedule", "change flight", "alternative flight"]
        )
        result["wants_hotel"] = "hotel" in lower
        result["wants_full_night_hotel"] = "full night" in lower and "hotel" in lower
        result["is_legal_threat"] = any(
            w in lower for w in ["sue", "legal", "lawyer", "court", "consumer forum"]
        )
        if result["wants_refund"] or result["wants_rebook"]:
            result["primary_intent"] = "refund" if result["wants_refund"] else "rebook"
        return result

    # ── Response generation ───────────────────────────────────────────────────

    def generate_response(self, prompt: str) -> str:
        """Generate a customer-facing response.  Falls back through model chain."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a professional, empathetic airline customer support agent. "
                    "Generate a clear, helpful response based exactly on the provided context. "
                    "Do NOT invent policies, offers, or compensations not listed in the context."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        for model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
            try:
                resp = self._groq.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.3,
                )
                return resp.choices[0].message.content.strip()
            except Exception as exc:
                logger.warning("Groq model %s failed response gen: %s", model, exc)

        return self._external_fallback(messages)

    def _external_fallback(self, messages: list) -> str:
        settings = self._settings
        if not settings.FALLBACK_API_URL or not settings.FALLBACK_API_KEY:
            return (
                "I apologize for the inconvenience. Our systems are temporarily "
                "unavailable. Please contact our support team for immediate assistance."
            )
        try:
            import httpx
            resp = httpx.post(
                f"{settings.FALLBACK_API_URL}/chat/completions",
                headers={"Authorization": f"Bearer {settings.FALLBACK_API_KEY}"},
                json={"messages": messages, "temperature": 0.3},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.error("External fallback LLM failed: %s", exc)
            return (
                "I apologize for the inconvenience. Our systems are temporarily "
                "unavailable. Please contact our support team for immediate assistance."
            )


# ── Test mock ─────────────────────────────────────────────────────────────────

class MockLLMClient:
    """
    Deterministic drop-in replacement used in tests.
    Pass intent_result to control extract_intents output,
    and response_text to control generate_response output.
    """

    def __init__(
        self,
        intent_result: Optional[dict] = None,
        response_text: str = "Mock agent response.",
    ) -> None:
        self._intent = {**_default_intents(), **(intent_result or {})}
        self._response = response_text

    def extract_intents(self, message: str) -> dict:  # noqa: ARG002
        return dict(self._intent)

    def generate_response(self, prompt: str) -> str:  # noqa: ARG002
        return self._response
