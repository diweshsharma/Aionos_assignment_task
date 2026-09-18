"""
LangGraph StateGraph definition.

Graph flow:
  extract_intents
    → lookup_booking
        → [error path] error_node → log_turn → END
        → retrieve_policy
            → evaluate_policy
                → authority_check
                    → [legal threat] escalate → generate_response → log_turn → END
                    → execute_action → escalate → generate_response → log_turn → END
"""

from __future__ import annotations

from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes import (
    make_extract_intents_node,
    make_lookup_booking_node,
    make_retrieve_policy_node,
    make_evaluate_policy_node,
    make_authority_check_node,
    make_execute_action_node,
    make_escalate_node,
    make_generate_response_node,
    make_log_turn_node,
    make_error_node,
)


def _route_after_lookup(state: AgentState) -> str:
    """Branch to error_node if PNR was not found."""
    return "error_node" if state.get("error") else "retrieve_policy"


def _route_after_authority(state: AgentState) -> str:
    """
    Legal threats skip execute_action and go straight to escalate.
    Everything else goes through execute_action first.
    """
    authority = state.get("authority_result") or {}
    if authority.get("immediate_escalate"):
        return "escalate"
    return "execute_action"


def create_graph(
    llm,
    policy_engine,
    rag,
    SessionLocal,
) -> "CompiledGraph":  # type: ignore[name-defined]
    """
    Build and compile the LangGraph agent.

    All dependencies are injected so the graph is fully testable with mocks.
    """
    workflow = StateGraph(AgentState)

    # ── Register nodes ────────────────────────────────────────────────────────
    workflow.add_node("extract_intents", make_extract_intents_node(llm))
    workflow.add_node("lookup_booking", make_lookup_booking_node(SessionLocal))
    workflow.add_node("retrieve_policy", make_retrieve_policy_node(rag))
    workflow.add_node("evaluate_policy", make_evaluate_policy_node(policy_engine))
    workflow.add_node("authority_check", make_authority_check_node(policy_engine))
    workflow.add_node("execute_action", make_execute_action_node(policy_engine))
    workflow.add_node("escalate", make_escalate_node())
    workflow.add_node("generate_response", make_generate_response_node(llm, policy_engine))
    workflow.add_node("log_turn", make_log_turn_node(SessionLocal))
    workflow.add_node("error_node", make_error_node(llm))

    # ── Entry point ───────────────────────────────────────────────────────────
    workflow.set_entry_point("extract_intents")

    # ── Edges ─────────────────────────────────────────────────────────────────
    workflow.add_edge("extract_intents", "lookup_booking")

    workflow.add_conditional_edges(
        "lookup_booking",
        _route_after_lookup,
        {
            "error_node": "error_node",
            "retrieve_policy": "retrieve_policy",
        },
    )

    workflow.add_edge("retrieve_policy", "evaluate_policy")
    workflow.add_edge("evaluate_policy", "authority_check")

    workflow.add_conditional_edges(
        "authority_check",
        _route_after_authority,
        {
            "execute_action": "execute_action",
            "escalate": "escalate",
        },
    )

    workflow.add_edge("execute_action", "escalate")
    workflow.add_edge("escalate", "generate_response")
    workflow.add_edge("generate_response", "log_turn")
    workflow.add_edge("log_turn", END)

    # Error path also terminates via generate_response → log_turn
    workflow.add_edge("error_node", "generate_response")

    return workflow.compile()
