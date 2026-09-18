"""
LangGraph node functions — each is a small, named, testable function.

Nodes receive the full AgentState and return a dict of the fields they update.
Dependencies (llm, policy_engine, rag, SessionLocal) are injected via factory
closures so tests can pass mocks without touching global state.
"""

from __future__ import annotations

import logging
from typing import Callable, Any

from agent.state import AgentState
from services import authority_guard as ag

logger = logging.getLogger(__name__)


# ── Utility: convert ORM objects to plain dicts ───────────────────────────────

def _customer_to_dict(customer) -> dict:
    return {
        "id": customer.id,
        "name": customer.name,
        "loyalty_tier": customer.loyalty_tier,
        "contact": customer.contact,
        "flights_last_12mo": customer.flights_last_12mo,
        "prior_complaints": customer.prior_complaints or [],
    }


def _booking_to_dict(booking) -> dict:
    return {
        "id": booking.id,
        "pnr": booking.pnr,
        "flight_number": booking.flight_number,
        "route_origin": booking.route_origin,
        "route_dest": booking.route_dest,
        "flight_date": str(booking.flight_date),
        "scheduled_departure": str(booking.scheduled_departure),
        "actual_departure": str(booking.actual_departure) if booking.actual_departure else None,
        "status": booking.status,
        "delay_hours": booking.delay_hours,
    }


# ── Node factories ─────────────────────────────────────────────────────────────

def make_extract_intents_node(llm) -> Callable[[AgentState], dict]:
    """Node 1 — LLM extracts structured intents from the customer message."""

    def extract_intents_node(state: AgentState) -> dict:
        logger.info("[NODE START] extract_intents | pnr=%s msg='%s'", state.get("pnr"), state.get("message"))
        try:
            intents = llm.extract_intents(state["message"])
            logger.info("[NODE END] extract_intents | intents=%s", intents)
            return {"intents": intents}
        except Exception as exc:
            logger.exception("[NODE ERROR] extract_intents failed: %s", exc)
            return {"intents": {}, "error": f"Intent extraction failed: {exc}"}

    return extract_intents_node


def make_lookup_booking_node(SessionLocal) -> Callable[[AgentState], dict]:
    """Node 2 — DB lookup: find customer + booking by PNR."""

    def lookup_booking_node(state: AgentState) -> dict:
        pnr = state.get("pnr", "")
        logger.info("[NODE START] lookup_booking | pnr=%s", pnr)
        db = SessionLocal()
        try:
            from services.booking_service import get_customer_by_pnr
            result = get_customer_by_pnr(pnr, db)
            if result is None:
                logger.warning("[NODE END] lookup_booking | PNR '%s' not found", pnr)
                return {"error": f"No booking found for PNR '{pnr}'. Please verify and try again."}
            customer, booking = result
            cust_dict = _customer_to_dict(customer)
            book_dict = _booking_to_dict(booking)
            
            # Retrieve prior conversation turns for multi-turn context
            history_list = []
            conv_id = state.get("conversation_id")
            if conv_id:
                from models import ConversationTurn
                turns = db.query(ConversationTurn).filter(ConversationTurn.conversation_id == conv_id).order_by(ConversationTurn.created_at.asc()).all()
                history_list = [{"role": t.role, "content": t.content} for t in turns]
            elif customer:
                from models import Conversation, ConversationTurn
                conv = db.query(Conversation).filter(Conversation.customer_id == customer.id).order_by(Conversation.started_at.desc()).first()
                if conv:
                    turns = db.query(ConversationTurn).filter(ConversationTurn.conversation_id == conv.id).order_by(ConversationTurn.created_at.asc()).all()
                    history_list = [{"role": t.role, "content": t.content} for t in turns]

            logger.info("[NODE END] lookup_booking | customer=%s history_turns=%d", cust_dict.get("name"), len(history_list))
            return {
                "customer": cust_dict,
                "booking": book_dict,
                "history": history_list,
            }
        except Exception as exc:
            logger.exception("[NODE ERROR] lookup_booking failed: %s", exc)
            return {"error": str(exc)}
        finally:
            db.close()

    return lookup_booking_node


def make_retrieve_policy_node(rag) -> Callable[[AgentState], dict]:
    """Node 3 — Chroma RAG: retrieve relevant policy context."""

    def retrieve_policy_node(state: AgentState) -> dict:
        booking = state.get("booking") or {}
        intents = state.get("intents") or {}
        status = booking.get("status", "")
        intent_str = intents.get("primary_intent", "info")
        logger.info("[NODE START] retrieve_policy | status=%s intent=%s", status, intent_str)
        query = f"Flight {status} {intent_str} policy compensation"
        context = rag.retrieve(query)
        logger.info("[NODE END] retrieve_policy | context_len=%d", len(context))
        return {"policy_context": context}

    return retrieve_policy_node


def make_evaluate_policy_node(policy_engine) -> Callable[[AgentState], dict]:
    """Node 4 — policy_engine: deterministic benefit calculation from YAML."""

    def evaluate_policy_node(state: AgentState) -> dict:
        booking = state.get("booking") or {}
        status = booking.get("status", "ON_TIME")
        delay_hours = booking.get("delay_hours")
        logger.info("[NODE START] evaluate_policy | status=%s delay_hours=%s", status, delay_hours)

        decision: dict[str, Any] = {"flight_status": status}

        if status == "CANCELLED":
            decision["delay_hours"] = None
            decision["entitled_benefits"] = []
            decision["cancellation_policy"] = policy_engine.get_cancellation_policy()

        elif status == "DELAYED" and delay_hours is not None:
            decision["delay_hours"] = delay_hours
            decision["entitled_benefits"] = policy_engine.get_delay_benefits(delay_hours)
            decision["cancellation_policy"] = None

        else:
            decision["delay_hours"] = None
            decision["entitled_benefits"] = []
            decision["cancellation_policy"] = None

        decision["fare_waiver_limit"] = policy_engine.get_fare_waiver_limit()
        logger.info("[NODE END] evaluate_policy | entitled=%s", decision.get("entitled_benefits"))
        return {"policy_decision": decision}

    return evaluate_policy_node


def make_authority_check_node(policy_engine) -> Callable[[AgentState], dict]:
    """Node 5 — authority_guard: determine what's allowed vs. must escalate."""

    def authority_check_node(state: AgentState) -> dict:
        logger.info("[NODE START] authority_check")
        intents = state.get("intents") or {}
        policy_decision = state.get("policy_decision") or {}
        message = state.get("message", "")

        allowed_actions: list[str] = []
        escalation_reasons: list[str] = []
        denied_non_escalated: list[str] = []
        immediate_escalate = False

        # ── Legal threat → immediate escalation ──────────────────────────────
        if intents.get("is_legal_threat") or ag.is_legal_threat(message):
            immediate_escalate = True
            escalation_reasons.append(
                "Legal action or formal complaint threat detected. "
                "This conversation has been immediately escalated to a supervisor."
            )
            logger.info("[NODE END] authority_check | immediate_escalate=True")
            return {
                "authority_result": {
                    "allowed_actions": [],
                    "escalation_reasons": escalation_reasons,
                    "immediate_escalate": True,
                    "denied_non_escalated": [],
                }
            }

        # ── Different payment method ─────────────────────────────────────────
        if intents.get("wants_different_payment_method") or ag.is_different_payment_method(message):
            escalation_reasons.append(
                "Customer requested a refund to a different payment method. "
                "Policy only allows refunds to the original payment method. "
                "Escalated to supervisor."
            )

        # ── Cancellation scenario ────────────────────────────────────────────
        status = policy_decision.get("flight_status", "ON_TIME")
        if status == "CANCELLED":
            if intents.get("wants_refund"):
                allowed_actions.append("offer_full_refund")
            if intents.get("wants_rebook") or not intents.get("wants_refund"):
                allowed_actions.append("offer_free_rebook")
            # Default: offer both options if customer hasn't specified
            if not allowed_actions:
                allowed_actions.extend(["offer_full_refund", "offer_free_rebook"])

        # ── Delay scenario ───────────────────────────────────────────────────
        elif status == "DELAYED":
            entitled = policy_decision.get("entitled_benefits", [])
            delay_hours = policy_decision.get("delay_hours", 0) or 0

            # Only process general delay benefits (vouchers, lounge, hotel) if:
            # 1. Customer asked for delay benefits / info / compensation / hotel, OR
            # 2. Customer didn't specify an explicit separate request (like fare waiver, refund, legal threat)
            wants_specific_other = (
                intents.get("fare_difference_waiver_inr") is not None or
                intents.get("wants_refund") or
                intents.get("wants_different_payment_method") or
                intents.get("is_legal_threat")
            )
            wants_delay_benefits = (
                intents.get("wants_hotel") or
                intents.get("wants_full_night_hotel") or
                intents.get("primary_intent") in ["compensation", "info"] or
                not wants_specific_other
            )

            if wants_delay_benefits:
                if "meal_voucher_500" in entitled:
                    allowed_actions.append("issue_meal_voucher_500")
                if "lounge_access" in entitled:
                    allowed_actions.append("grant_lounge_access")

                # Hotel handling
                if intents.get("wants_hotel") or intents.get("wants_full_night_hotel"):
                    hotel_ok, full_night_esc, explanation = ag.check_hotel_entitlement(
                        delay_hours, entitled, bool(intents.get("wants_full_night_hotel"))
                    )
                    if hotel_ok:
                        allowed_actions.append("provide_hotel_delayed_hours")
                        if full_night_esc:
                            escalation_reasons.append(explanation)
                    else:
                        denied_non_escalated.append(explanation)
                elif "hotel_delayed_hours" in entitled and (not wants_specific_other or intents.get("primary_intent") == "compensation"):
                    allowed_actions.append("provide_hotel_delayed_hours")

        # ── Fare-difference waiver ────────────────────────────────────────────
        fare_waiver_ask = intents.get("fare_difference_waiver_inr")
        if fare_waiver_ask is not None:
            limit = policy_engine.get_fare_waiver_limit()
            within, explanation = ag.check_fare_waiver(float(fare_waiver_ask), limit)
            if within:
                allowed_actions.append(f"waive_fare_difference_{int(fare_waiver_ask)}_inr")
            else:
                escalation_reasons.append(explanation)

        # ── Extra compensation asks ───────────────────────────────────────────
        extra_asks = intents.get("extra_compensation_asks", [])
        if extra_asks:
            has_unauth, details = ag.check_extra_compensation(extra_asks)
            if has_unauth:
                for d in details:
                    escalation_reasons.append(d["escalation_reason"])

        logger.info("[NODE END] authority_check | allowed=%s escalations=%d", allowed_actions, len(escalation_reasons))
        return {
            "authority_result": {
                "allowed_actions": allowed_actions,
                "escalation_reasons": escalation_reasons,
                "immediate_escalate": immediate_escalate,
                "denied_non_escalated": denied_non_escalated,
            }
        }

    return authority_check_node


def make_execute_action_node(policy_engine) -> Callable[[AgentState], dict]:
    """Node 6 — execute all allowed actions and build the actions_taken list."""

    def execute_action_node(state: AgentState) -> dict:
        authority = state.get("authority_result") or {}
        allowed = authority.get("allowed_actions", [])
        booking = state.get("booking") or {}
        policy_decision = state.get("policy_decision") or {}
        logger.info("[NODE START] execute_action | allowed_count=%d", len(allowed))
        actions_taken = []

        for action in allowed:
            if action == "offer_full_refund":
                refund_policy = policy_engine.get_refund_policy()
                actions_taken.append({
                    "type": "full_refund_offered",
                    "details": {
                        "processing_days": refund_policy["processing_days"],
                        "to": "original_payment_method",
                        "note": "Full refund to original payment method.",
                    },
                })

            elif action == "offer_free_rebook":
                cp = policy_engine.get_cancellation_policy()
                actions_taken.append({
                    "type": "free_rebook_offered",
                    "details": {
                        "flight": booking.get("flight_number"),
                        "window_hours": cp["rebook_window_hours"],
                        "note": f"Free rebook on next available flight within {cp['rebook_window_hours']} hours.",
                    },
                })

            elif action == "issue_meal_voucher_500":
                actions_taken.append({
                    "type": "meal_voucher_issued",
                    "details": {"amount_inr": 500},
                })

            elif action == "grant_lounge_access":
                actions_taken.append({
                    "type": "lounge_access_granted",
                    "details": {},
                })

            elif action == "provide_hotel_delayed_hours":
                delay_h = policy_decision.get("delay_hours", 0)
                actions_taken.append({
                    "type": "hotel_provided_delayed_hours",
                    "details": {
                        "delay_hours": delay_h,
                        "note": f"Hotel accommodation for {delay_h:.1f}-hour delay period only (not full night).",
                    },
                })

            elif action.startswith("waive_fare_difference_"):
                amount = action.split("_")[-2]
                actions_taken.append({
                    "type": "fare_difference_waived",
                    "details": {"amount_inr": int(amount)},
                })

        logger.info("[NODE END] execute_action | executed_count=%d", len(actions_taken))
        return {"actions_taken": actions_taken}

    return execute_action_node


def make_escalate_node() -> Callable[[AgentState], dict]:
    """Node 7 — collect all escalation reasons into the escalations list."""

    def escalate_node(state: AgentState) -> dict:
        authority = state.get("authority_result") or {}
        reasons = authority.get("escalation_reasons", [])
        logger.info("[NODE START & END] escalate | reasons_count=%d", len(reasons))
        return {"escalations": reasons}

    return escalate_node


def make_generate_response_node(llm, policy_engine) -> Callable[[AgentState], dict]:
    """Node 8 — LLM drafts the final customer-facing message from structured context."""

    def _build_prompt(state: AgentState) -> str:
        customer = state.get("customer") or {}
        booking = state.get("booking") or {}
        policy_decision = state.get("policy_decision") or {}
        authority = state.get("authority_result") or {}
        actions = state.get("actions_taken", [])
        escalations = state.get("escalations", [])
        denied = authority.get("denied_non_escalated", [])
        error = state.get("error")

        if error:
            return (
                f"The customer provided PNR '{state['pnr']}' but we could not find it. "
                "Inform them politely and ask them to verify the PNR."
            )

        action_lines = "\n".join(
            f"  - {a['type']}: {a.get('details', {})}" for a in actions
        ) or "  (none)"

        escalation_lines = "\n".join(
            f"  - {r}" for r in escalations
        ) or "  (none)"

        denied_lines = "\n".join(
            f"  - {d}" for d in denied
        ) or "  (none)"

        history = state.get("history") or []
        history_lines = "\n".join(
            f"  - {h['role'].upper()}: {h['content']}" for h in history[-6:]
        ) or "  (first message)"

        return f"""
You are responding to an airline customer support request.

CUSTOMER: {customer.get('name', 'Customer')} ({customer.get('loyalty_tier', 'Standard')} tier)
FLIGHT: {booking.get('flight_number')} | {booking.get('route_origin')} → {booking.get('route_dest')} | DATE: {booking.get('flight_date')} | STATUS: {booking.get('status')}
{'DELAY: ' + str(booking.get('delay_hours')) + ' hours' if booking.get('delay_hours') else ''}

RECENT CONVERSATION HISTORY:
{history_lines}

NEW CUSTOMER MESSAGE: "{state.get('message', '')}"

ACTIONS TAKEN (confirmed system actions):
{action_lines}

ITEMS DECLINED:
{denied_lines}

ITEMS ESCALATED TO SUPERVISOR:
{escalation_lines}

RULES FOR REPLY TEXT (CRITICAL):
1. Write ONLY a short, natural-language reply in empathetic conversational dialogue.
2. NO salutations like "Dear [Name] ([Tier] tier)". Use first name naturally if appropriate.
3. NO inline bulleted lists of policy rules or "Policy Rules Applied:".
4. NO literal labels like "Human Supervisor Review Flagged:" or "Escalated:". Say it conversationally ("I've flagged that for a supervisor to review with you").
5. Follow the natural 4-step structure:
   (a) Acknowledge & empathize with the disruption.
   (b) State what was found/confirmed regarding the flight.
   (c) State what actions were processed or what options are available.
   (d) State plainly what cannot be done and what happens next.
6. If the customer message is brief gratitude ("thanks", "ok"), respond warmly without repeating policy details.
7. If the customer asks a follow-up ("why can't you give full night?"), answer conversationally using the prior turns context.
""".strip()

    def generate_response_node(state: AgentState) -> dict:
        logger.info("[NODE START] generate_response")
        prompt = _build_prompt(state)
        response = llm.generate_response(prompt)
        logger.info("[NODE END] generate_response | len=%d", len(response))
        return {"response": response}

    return generate_response_node


def make_log_turn_node(SessionLocal) -> Callable[[AgentState], dict]:
    """Node 9 — persist conversation turn and all action/escalation logs to DB."""

    def log_turn_node(state: AgentState) -> dict:
        logger.info("[NODE START] log_turn")
        db = SessionLocal()
        try:
            from services.booking_service import (
                get_or_create_conversation,
                log_turn as _log_turn, log_action,
            )

            conv_id = state.get("conversation_id")

            # Resolve customer_id
            customer = state.get("customer")
            customer_id = customer["id"] if customer else None

            if customer_id and not conv_id:
                conv = get_or_create_conversation(customer_id, db)
                conv_id = conv.id
            elif not customer_id:
                logger.warning("[NODE END] log_turn | No customer_id to log turn")
                return {"conversation_id": None}

            # Log user turn
            _log_turn(conv_id, "user", state.get("message", ""), db)

            # Log agent turn
            response = state.get("response") or state.get("error") or ""
            _log_turn(conv_id, "agent", response, db)

            # Log actions
            for action in state.get("actions_taken", []):
                log_action(conv_id, action["type"], action.get("details", {}), False, db)

            # Log escalations ALWAYS as action_type="escalation_flagged" with escalated=True
            for reason in state.get("escalations", []):
                log_action(conv_id, "escalation_flagged", {"reason": reason}, True, db)

            logger.info("[NODE END] log_turn | conv_id=%s actions_logged=%d escalations_logged=%d",
                        conv_id, len(state.get("actions_taken", [])), len(state.get("escalations", [])))

            return {"conversation_id": conv_id}

        except Exception as exc:
            logger.exception("[NODE ERROR] log_turn error: %s", exc)
            db.rollback()
            return {"conversation_id": state.get("conversation_id")}
        finally:
            db.close()

    return log_turn_node


def make_error_node(llm) -> Callable[[AgentState], dict]:
    """Error path — generates a polite not-found response."""

    def error_node(state: AgentState) -> dict:
        logger.info("[NODE START & END] error_node | pnr=%s", state.get("pnr"))
        response = llm.generate_response(
            f"The customer provided PNR '{state['pnr']}' but no booking was found. "
            "Please generate a polite response asking them to verify their PNR."
        )
        return {"response": response}

    return error_node
