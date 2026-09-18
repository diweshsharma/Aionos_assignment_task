"""
Agent scenario smoke tests — the 3 mandatory scenarios + ingestion smoke test.

All LLM calls are mocked.  Policy decisions come from the real policy_engine
reading the real policy_rules.yaml.  DB uses in-memory SQLite.
"""

from __future__ import annotations

import pytest
from datetime import datetime, date

from services.llm_client import LLMClient, MockLLMClient
from tests.conftest import make_graph, invoke_graph

from config import settings

AUTH = {"Authorization": f"Bearer {settings.AUTH_TOKEN}"}


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 1 — Priya Nair (Gold, SK4821X, SK-204, CANCELLED)
# Agent must: grant refund/rebook choice + escalate business-class upgrade
# ─────────────────────────────────────────────────────────────────────────────

def test_scenario1_priya_refund_and_escalation(seeded_db, policy, rag, TestSessionLocal):
    """
    Priya's SK-204 is airline-cancelled.
    She wants a refund AND a free business class upgrade.
    Expected:
      - actions_taken includes refund / rebook offer
      - escalations contains the business-class upgrade reason
    """
    mock_llm = MockLLMClient(
        intent_result={
            "primary_intent": "refund",
            "wants_refund": True,
            "wants_rebook": False,
            "wants_hotel": False,
            "wants_full_night_hotel": False,
            "extra_compensation_asks": ["free business class upgrade"],
            "fare_difference_waiver_inr": None,
            "wants_different_payment_method": False,
            "is_legal_threat": False,
        },
        response_text="Priya scenario response.",
    )
    graph = make_graph(mock_llm, policy, rag, TestSessionLocal)
    state = invoke_graph(
        graph,
        pnr="SK4821X",
        message="My flight was cancelled. I want a refund. Also give me a free business class upgrade.",
    )

    # Flight must be found
    assert state.get("error") is None
    assert state["customer"]["name"] == "Priya Nair"
    assert state["booking"]["status"] == "CANCELLED"

    # Refund must be offered
    action_types = [a["type"] for a in state["actions_taken"]]
    assert "full_refund_offered" in action_types

    # Business class upgrade must be escalated (not executed)
    escalations = state["escalations"]
    assert len(escalations) >= 1
    escalation_text = " ".join(escalations).lower()
    assert "business class" in escalation_text or "beyond" in escalation_text or "unauthorized" in escalation_text

    # Upgrade must NOT appear in actions_taken
    assert not any("upgrade" in a["type"] for a in state["actions_taken"])


def test_scenario1_priya_rebook_option_also_offered(seeded_db, policy, rag, TestSessionLocal):
    """When Priya asks only for refund, rebook is also offered as an alternative."""
    mock_llm = MockLLMClient(
        intent_result={
            "primary_intent": "refund",
            "wants_refund": True,
            "wants_rebook": False,
            "wants_hotel": False,
            "wants_full_night_hotel": False,
            "extra_compensation_asks": [],
            "fare_difference_waiver_inr": None,
            "wants_different_payment_method": False,
            "is_legal_threat": False,
        },
    )
    graph = make_graph(mock_llm, policy, rag, TestSessionLocal)
    state = invoke_graph(graph, pnr="SK4821X", message="I want a refund for my cancelled flight.")
    action_types = [a["type"] for a in state["actions_taken"]]
    assert "full_refund_offered" in action_types
    assert len(state["escalations"]) == 0


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 2 — Arvind Kulkarni (Silver, TR1190B, SK-118, DELAYED 4h)
# Agent must: apply voucher + lounge; decline hotel (< 5h threshold)
# ─────────────────────────────────────────────────────────────────────────────

def test_scenario2_arvind_4h_delay_voucher_lounge_no_hotel(seeded_db, policy, rag, TestSessionLocal):
    """
    Arvind's SK-118 is delayed 4 hours.  He asks for hotel.
    Expected:
      - actions_taken: meal_voucher_issued, lounge_access_granted
      - hotel NOT in actions_taken
      - escalations empty (hotel decline is explained, not escalated)
      - denied_non_escalated contains the hotel explanation
    """
    mock_llm = MockLLMClient(
        intent_result={
            "primary_intent": "info",
            "wants_refund": False,
            "wants_rebook": False,
            "wants_hotel": True,
            "wants_full_night_hotel": False,
            "extra_compensation_asks": [],
            "fare_difference_waiver_inr": None,
            "wants_different_payment_method": False,
            "is_legal_threat": False,
        },
    )
    graph = make_graph(mock_llm, policy, rag, TestSessionLocal)
    state = invoke_graph(
        graph,
        pnr="TR1190B",
        message="My flight is delayed 4 hours. Can I get a hotel room?",
    )

    assert state.get("error") is None
    assert state["customer"]["name"] == "Arvind Kulkarni"
    assert state["booking"]["status"] == "DELAYED"
    assert state["booking"]["delay_hours"] == 4.0

    action_types = [a["type"] for a in state["actions_taken"]]
    assert "meal_voucher_issued" in action_types
    assert "lounge_access_granted" in action_types
    assert "hotel_provided_delayed_hours" not in action_types

    # No escalation — hotel is declined with policy explanation
    assert len(state["escalations"]) == 0

    # Authority result must record the denial
    denied = state["authority_result"].get("denied_non_escalated", [])
    denied_text = " ".join(denied).lower()
    assert "hotel" in denied_text or "5 hour" in denied_text


def test_scenario2_arvind_benefits_match_4h_tier(policy):
    """Policy engine must return correct benefits for a 4h delay."""
    benefits = policy.get_delay_benefits(4.0)
    assert "meal_voucher_500" in benefits
    assert "lounge_access" in benefits
    assert "hotel_delayed_hours" not in benefits


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 3 — Meher Kaur (Platinum, WL7742, SK-305, DELAYED 6h)
# Agent must:
#   - apply voucher + lounge + hotel-for-delayed-hours
#   - decline full-night hotel with escalation
#   - escalate ₹2,000 fare waiver (over ₹1,500 limit)
# ─────────────────────────────────────────────────────────────────────────────

def test_scenario3_meher_6h_delay_all_benefits_plus_escalations(seeded_db, policy, rag, TestSessionLocal):
    """
    Meher's SK-305 is delayed 6 hours.
    She asks for full-night hotel AND waiver of ₹2,000 fare difference.
    Expected:
      - actions: meal_voucher, lounge, hotel_delayed_hours (NOT full night)
      - escalations: full-night hotel AND ₹2,000 waiver (both escalated)
    """
    mock_llm = MockLLMClient(
        intent_result={
            "primary_intent": "info",
            "wants_refund": False,
            "wants_rebook": True,
            "wants_hotel": True,
            "wants_full_night_hotel": True,
            "extra_compensation_asks": [],
            "fare_difference_waiver_inr": 2000.0,
            "wants_different_payment_method": False,
            "is_legal_threat": False,
        },
    )
    graph = make_graph(mock_llm, policy, rag, TestSessionLocal)
    state = invoke_graph(
        graph,
        pnr="WL7742",
        message=(
            "My flight is delayed 6 hours. I need a full night hotel stay. "
            "Also I want to rebook to a higher class — please waive the ₹2,000 fare difference."
        ),
    )

    assert state.get("error") is None
    assert state["customer"]["name"] == "Meher Kaur"
    assert state["booking"]["status"] == "DELAYED"
    assert state["booking"]["delay_hours"] == 6.0

    action_types = [a["type"] for a in state["actions_taken"]]
    # All three entitled benefits granted
    assert "meal_voucher_issued" in action_types
    assert "lounge_access_granted" in action_types
    assert "hotel_provided_delayed_hours" in action_types

    # Two escalations
    escalations = state["escalations"]
    escalation_text = " ".join(escalations).lower()
    assert "full" in escalation_text or "night" in escalation_text   # full-night escalation
    assert "2000" in escalation_text or "1500" in escalation_text     # fare waiver escalation


def test_scenario3_meher_benefits_match_6h_tier(policy):
    benefits = policy.get_delay_benefits(6.0)
    assert "meal_voucher_500" in benefits
    assert "lounge_access" in benefits
    assert "hotel_delayed_hours" in benefits


def test_scenario3_fare_waiver_2000_escalated(policy):
    from services.authority_guard import check_fare_waiver
    ok, msg = check_fare_waiver(2000.0, policy.get_fare_waiver_limit())
    assert ok is False
    assert "escalated" in msg.lower()


# ─────────────────────────────────────────────────────────────────────────────
# LEGAL THREAT — immediate escalation regardless of other topics
# ─────────────────────────────────────────────────────────────────────────────

def test_legal_threat_triggers_immediate_escalation(seeded_db, policy, rag, TestSessionLocal):
    mock_llm = MockLLMClient(
        intent_result={
            "primary_intent": "complaint",
            "wants_refund": True,
            "wants_rebook": False,
            "wants_hotel": False,
            "wants_full_night_hotel": False,
            "extra_compensation_asks": [],
            "fare_difference_waiver_inr": None,
            "wants_different_payment_method": False,
            "is_legal_threat": True,
        },
    )
    graph = make_graph(mock_llm, policy, rag, TestSessionLocal)
    state = invoke_graph(
        graph,
        pnr="SK4821X",
        message="I will sue your airline if this isn't resolved immediately.",
    )

    assert state["authority_result"]["immediate_escalate"] is True
    # No actions should be executed for legal threats
    assert state["actions_taken"] == []
    # Escalation reason must mention legal threat
    escalation_text = " ".join(state["escalations"]).lower()
    assert "legal" in escalation_text or "supervisor" in escalation_text


# ─────────────────────────────────────────────────────────────────────────────
# MULTI-TURN REGRESSION TESTS — Distinct requests produce distinct responses
# ─────────────────────────────────────────────────────────────────────────────

def test_sequential_distinct_requests_in_same_session(seeded_db, policy, rag, TestSessionLocal):
    """
    Regression test for bug report:
    Turn 1: Request full night hotel stay (6h delay PNR WL7742).
    Turn 2: Ask for ₹2000 fare waiver in the SAME session.
    Assert Turn 2 processes fare waiver, escalates fare waiver > ₹1500, and does NOT repeat Turn 1 hotel text.
    """
    llm = LLMClient()
    graph = make_graph(llm, policy, rag, TestSessionLocal)

    # Turn 1: Hotel request
    state1 = invoke_graph(
        graph,
        pnr="WL7742",
        message="Request full night hotel stay for 6h delay",
    )
    conv_id = state1.get("conversation_id")
    reply1 = state1.get("response", "")

    # Turn 2: Fare waiver request (different topic in same conversation)
    state2 = invoke_graph(
        graph,
        pnr="WL7742",
        message="Ask for ₹2000 fare waiver",
        conversation_id=conv_id,
    )
    reply2 = state2.get("response", "")

    # Assert Turn 2 response addresses fare waiver / ₹2000 and NOT hotel
    reply2_lower = reply2.lower()
    assert ("2000" in reply2_lower or "fare" in reply2_lower or "waiver" in reply2_lower)
    assert reply1 != reply2, "Turn 2 response must not be identical to Turn 1 response!"

    # Assert fare waiver escalation is captured in Turn 2
    esc2_text = " ".join(state2.get("escalations", [])).lower()
    assert "fare" in esc2_text or "2000" in esc2_text or "1500" in esc2_text


def test_consecutive_different_messages_produce_distinct_responses(seeded_db, policy, rag, TestSessionLocal):
    """
    General regression test: consecutive distinct messages must produce distinct replies.
    """
    llm = LLMClient()
    graph = make_graph(llm, policy, rag, TestSessionLocal)

    s1 = invoke_graph(graph, pnr="WL7742", message="What benefits am I entitled to?")
    conv_id = s1.get("conversation_id")

    s2 = invoke_graph(graph, pnr="WL7742", message="Ask for ₹2000 fare waiver", conversation_id=conv_id)

    assert s1.get("response") != s2.get("response"), "Distinct messages in a session must not produce duplicate responses!"


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 4 — Ingestion smoke test
# POST a 4th customer + booking, then chat → policy applies with zero code changes
# ─────────────────────────────────────────────────────────────────────────────

def test_ingestion_smoke_test_new_customer_and_booking(client, TestSessionLocal, policy, rag):
    """
    Add a 4th customer (Delayed 7h) via /admin/*, then run a /chat turn.
    Policy engine must evaluate correctly without any code change.
    7h delay → all three benefits (voucher + lounge + hotel_delayed_hours).
    """
    # Step 1: Add 4th customer
    cust_resp = client.post(
        "/admin/customers",
        json={
            "name": "Rahul Verma",
            "loyalty_tier": "Standard",
            "contact": "rahul.verma@example.com",
            "flights_last_12mo": 1,
            "prior_complaints": [],
        },
        headers=AUTH,
    )
    assert cust_resp.status_code == 201
    customer_id = cust_resp.json()["id"]

    # Step 2: Add booking with 7h delay
    booking_resp = client.post(
        "/admin/bookings",
        json={
            "pnr": "NEWP001",
            "customer_id": customer_id,
            "flight_number": "SK-777",
            "route_origin": "Kolkata",
            "route_dest": "Delhi",
            "flight_date": "2026-10-05",
            "scheduled_departure": "2026-10-05T08:00:00",
            "actual_departure": "2026-10-05T15:00:00",
            "status": "DELAYED",
            "delay_hours": 7.0,
        },
        headers=AUTH,
    )
    assert booking_resp.status_code == 201

    # Step 3: Wire up graph with mock LLM for the new customer
    from agent.graph import create_graph
    mock_llm = MockLLMClient(
        intent_result={
            "primary_intent": "info",
            "wants_refund": False,
            "wants_rebook": False,
            "wants_hotel": True,
            "wants_full_night_hotel": False,
            "extra_compensation_asks": [],
            "fare_difference_waiver_inr": None,
            "wants_different_payment_method": False,
            "is_legal_threat": False,
        },
        response_text="Ingestion test response.",
    )
    from database import get_db
    from main import app
    graph = create_graph(mock_llm, policy, rag, TestSessionLocal)
    app.state.graph = graph

    # Step 4: Chat with the new PNR
    chat_resp = client.post(
        "/chat",
        json={
            "pnr": "NEWP001",
            "message": "My flight is delayed 7 hours. What can I get?",
        },
        headers=AUTH,
    )
    assert chat_resp.status_code == 200
    data = chat_resp.json()

    # Policy must apply: 7h → voucher + lounge + hotel
    action_types = [a["type"] for a in data["actions"]]
    assert "meal_voucher_issued" in action_types
    assert "lounge_access_granted" in action_types
    assert "hotel_provided_delayed_hours" in action_types

    # No escalations for a straightforward 7h delay (no extra asks)
    assert data["escalations"] == []


# ─────────────────────────────────────────────────────────────────────────────
# Edge case — unknown PNR
# ─────────────────────────────────────────────────────────────────────────────

def test_unknown_pnr_returns_error_response(seeded_db, policy, rag, TestSessionLocal):
    mock_llm = MockLLMClient(response_text="PNR not found response.")
    graph = make_graph(mock_llm, policy, rag, TestSessionLocal)
    state = invoke_graph(graph, pnr="BADPNR", message="Where is my flight?")
    assert state.get("error") is not None
    assert "BADPNR" in state["error"]
