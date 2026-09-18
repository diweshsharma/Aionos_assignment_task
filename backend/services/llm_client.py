"""
LLM client — wraps Groq (primary + fallback model) and an optional
external OpenAI-compatible endpoint as a final fallback.

The mock class at the bottom is used in tests without any network calls.
"""

from __future__ import annotations

import json
import logging
import re
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
        """Use LLM to extract structured intents. Falls back through model chain."""
        if not self._settings.GROQ_API_KEY or "placeholder" in self._settings.GROQ_API_KEY.lower():
            return self._keyword_intents(message)

        messages = [
            {"role": "system", "content": _INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]
        for model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama3-70b-8192", "llama3-8b-8192"]:
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

        # Keyword-based last resort
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
            w in lower for w in ["sue", "legal", "lawyer", "court", "consumer forum", "legal action"]
        )
        result["wants_different_payment_method"] = any(
            w in lower for w in ["different card", "another card", "another account", "different bank", "different upi"]
        )

        extra_asks = []
        if any(w in lower for w in ["upgrade", "business class", "first class"]):
            extra_asks.append("free business class upgrade")
        if any(w in lower for w in ["extra cash", "cash compensation", "additional cash"]):
            extra_asks.append("extra cash compensation")
        result["extra_compensation_asks"] = extra_asks

        # Extract fare waiver INR if present
        match = re.search(r'(?:₹|rs\.?|inr)\s*(\d+)', lower)
        if match:
            result["fare_difference_waiver_inr"] = float(match.group(1))

        if result["wants_refund"] or result["wants_rebook"]:
            result["primary_intent"] = "refund" if result["wants_refund"] else "rebook"
        return result

    # ── Response generation ───────────────────────────────────────────────────

    def generate_response(self, prompt: str) -> str:
        """Generate a customer-facing response. Falls back through model chain."""
        if not self._settings.GROQ_API_KEY or "placeholder" in self._settings.GROQ_API_KEY.lower():
            return self._build_structured_fallback_response(prompt)

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
        for model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama3-70b-8192", "llama3-8b-8192"]:
            try:
                resp = self._groq.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.3,
                )
                return resp.choices[0].message.content.strip()
            except Exception as exc:
                logger.warning("Groq model %s failed response gen: %s", model, exc)

        return self._external_fallback(messages, prompt)

    def _external_fallback(self, messages: list, original_prompt: str) -> str:
        settings = self._settings
        if settings.FALLBACK_API_URL and settings.FALLBACK_API_KEY:
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

        return self._build_structured_fallback_response(original_prompt)

    def _build_structured_fallback_response(self, prompt: str) -> str:
        """Build short, natural conversational language following 4-step support structure."""
        cust_match = re.search(r'CUSTOMER:\s*([^\(\n]+)', prompt)
        name_full = cust_match.group(1).strip() if cust_match else ""
        first_name = name_full.split()[0] if name_full and name_full != "Customer" else ""

        flight_match = re.search(r'FLIGHT:\s*([^\n|]+)', prompt)
        flight_no = flight_match.group(1).strip() if flight_match else "your flight"

        status_match = re.search(r'STATUS:\s*([^\n]+)', prompt)
        status = status_match.group(1).strip() if status_match else ""
        
        delay_match = re.search(r'DELAY:\s*([\d\.]+)\s*hours', prompt)
        delay_h = delay_match.group(1) if delay_match else None

        msg_match = re.search(r'CUSTOMER MESSAGE:\s*"([^"]+)"', prompt)
        cust_msg = msg_match.group(1).lower() if msg_match else ""

        # Small talk / gratitude check
        if any(w in cust_msg for w in ["thank", "thanks", "ok", "okay", "great", "bye"]) and len(cust_msg.split()) < 5:
            return f"You're very welcome{' ' + first_name if first_name else ''}! Please let me know if there's anything else I can help you with regarding your flight."

        # Parse actions taken
        actions_section = ""
        actions_match = re.search(r'ACTIONS TAKEN[^\n]*\n(.*?)(?=\n\n|\n[A-Z\s]+:|$)', prompt, re.DOTALL)
        if actions_match:
            actions_section = actions_match.group(1).strip()

        # Parse items declined
        declined_section = ""
        declined_match = re.search(r'ITEMS DECLINED[^\n]*\n(.*?)(?=\n\n|\n[A-Z\s]+:|$)', prompt, re.DOTALL)
        if declined_match:
            declined_section = declined_match.group(1).strip()

        # Parse escalations
        escalations_section = ""
        esc_match = re.search(r'ITEMS ESCALATED[^\n]*\n(.*?)(?=\n\n|\n[A-Z\s]+:|$)', prompt, re.DOTALL)
        if esc_match:
            escalations_section = esc_match.group(1).strip()

        action_phrases = []
        if actions_section and "(none)" not in actions_section:
            for line in actions_section.split("\n"):
                line_str = line.strip()
                if not line_str or line_str.startswith("(none)"):
                    continue
                if "full_refund_offered" in line_str:
                    action_phrases.append("processed a full refund offer to your original payment method")
                elif "free_rebook_offered" in line_str:
                    action_phrases.append("arranged a free rebooking option on the next available flight")
                elif "meal_voucher" in line_str:
                    action_phrases.append("issued a ₹500 meal voucher")
                elif "lounge_access" in line_str:
                    action_phrases.append("granted airport lounge access")
                elif "hotel" in line_str:
                    action_phrases.append("provided hotel coverage for the delayed hours")
                elif "fare_difference_waived" in line_str:
                    action_phrases.append("waived the fare difference for your flight change")

        sentences = []

        # 1. Empathize & State Findings
        greeting_name = f", {first_name}" if first_name else ""
        if status == "CANCELLED":
            sentences.append(f"I'm really sorry to hear about the cancellation of flight {flight_no}{greeting_name}.")
        elif delay_h:
            sentences.append(f"I'm really sorry about the {delay_h}-hour delay on flight {flight_no}{greeting_name} — that's a long wait.")
        else:
            sentences.append(f"I completely understand your concern regarding flight {flight_no}{greeting_name}.")

        # 2. State Actions Taken / Options
        if action_phrases:
            if len(action_phrases) == 1:
                sentences.append(f"I've {action_phrases[0]} for your booking.")
            elif len(action_phrases) == 2:
                sentences.append(f"I've {action_phrases[0]} and {action_phrases[1]}.")
            else:
                joined = ", ".join(action_phrases[:-1]) + f", and {action_phrases[-1]}"
                sentences.append(f"I've {joined}.")
        elif status == "CANCELLED":
            sentences.append("I can process a full refund to your original payment method or rebook you on the next available flight at no extra cost. Which would you prefer?")

        # 3. Declined & Escalations (conversational plain language)
        if escalations_section and "(none)" not in escalations_section:
            if "full night" in escalations_section.lower() or "hotel" in escalations_section.lower():
                sentences.append("A full night's stay isn't something I'm able to approve directly, so I've flagged that for a supervisor to review with you.")
            elif "different payment" in escalations_section.lower() or "payment method" in escalations_section.lower():
                sentences.append("Refunding to a different payment method requires secondary review, so I've escalated your request to a supervisor.")
            else:
                sentences.append("Your request requires specialist review, so I've flagged it for a supervisor to follow up with you directly.")

        if declined_section and "(none)" not in declined_section:
            if "policy" in declined_section.lower() or "limit" in declined_section.lower():
                sentences.append("Please note that additional compensation beyond our standard delay policy cannot be applied automatically.")

        return " ".join(sentences)


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

    def extract_intents(self, _message: str) -> dict:
        return dict(self._intent)

    def generate_response(self, _prompt: str) -> str:
        return self._response
