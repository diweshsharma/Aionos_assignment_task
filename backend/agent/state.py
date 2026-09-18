"""AgentState TypedDict — flows through every LangGraph node."""

from typing import TypedDict, Optional, Any


class AgentState(TypedDict):
    # ── Input ─────────────────────────────────────────────────────────────────
    pnr: str
    message: str
    conversation_id: Optional[int]

    # ── Extracted by extract_intents node (LLM) ───────────────────────────────
    intents: Optional[dict[str, Any]]
    # Shape:
    # {
    #   "primary_intent": str,
    #   "wants_refund": bool,
    #   "wants_rebook": bool,
    #   "wants_hotel": bool,
    #   "wants_full_night_hotel": bool,
    #   "extra_compensation_asks": list[str],
    #   "fare_difference_waiver_inr": float | None,
    #   "wants_different_payment_method": bool,
    #   "is_legal_threat": bool,
    # }

    # ── Populated by lookup_booking node ─────────────────────────────────────
    customer: Optional[dict[str, Any]]
    booking: Optional[dict[str, Any]]

    # ── Populated by retrieve_policy node (Chroma RAG) ───────────────────────
    policy_context: Optional[str]

    # ── Populated by evaluate_policy node (policy_engine, deterministic) ─────
    policy_decision: Optional[dict[str, Any]]
    # Shape:
    # {
    #   "flight_status": str,
    #   "delay_hours": float | None,
    #   "entitled_benefits": list[str],
    #   "cancellation_policy": dict | None,
    # }

    # ── Populated by authority_check node ────────────────────────────────────
    authority_result: Optional[dict[str, Any]]
    # Shape:
    # {
    #   "allowed_actions": list[str],
    #   "escalation_reasons": list[str],
    #   "immediate_escalate": bool,      ← True for legal threats
    #   "denied_non_escalated": list[str], ← items declined + explained (no supervisor)
    # }

    # ── Populated by execute_action / escalate nodes ──────────────────────────
    actions_taken: list[dict[str, Any]]
    escalations: list[str]

    # ── Populated by generate_response node (LLM) ─────────────────────────────
    response: Optional[str]

    # ── Error path ────────────────────────────────────────────────────────────
    error: Optional[str]
