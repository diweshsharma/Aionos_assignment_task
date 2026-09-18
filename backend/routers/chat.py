"""
Chat router — POST /chat and GET /conversations/{customer_id}.

The LangGraph compiled graph and services are loaded at app startup and
injected via FastAPI's app.state so they are not re-created per request.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from database import get_db
from schemas.chat import ChatRequest, ChatResponse, ActionDetail, ConversationOut, ConversationTurnOut
from services.booking_service import get_conversations_by_customer
from routers.deps import require_auth

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    request: Request,
    _: None = Depends(require_auth),
    db=Depends(get_db),
):
    """
    Main chat endpoint. Invokes the LangGraph agent and returns the response,
    the list of actions taken, customer/booking metadata, and escalation reasons.
    """
    graph = request.app.state.graph

    initial_state = {
        "pnr": body.pnr.strip().upper(),
        "message": body.message,
        "conversation_id": body.conversation_id,
        "intents": None,
        "customer": None,
        "booking": None,
        "policy_context": None,
        "policy_decision": None,
        "authority_result": None,
        "actions_taken": [],
        "escalations": [],
        "response": None,
        "error": None,
    }

    try:
        final_state = graph.invoke(initial_state)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent error: {exc}",
        )

    actions = [
        ActionDetail(type=a["type"], details=a.get("details", {}), escalated=a.get("escalated", False))
        for a in final_state.get("actions_taken", [])
    ]

    escalations_raw = final_state.get("escalations", [])
    escalations_formatted = [
        {"reason": e} if isinstance(e, str) else e
        for e in escalations_raw
    ]

    resp_text = final_state.get("response") or final_state.get("error") or "No response generated."

    customer = final_state.get("customer")
    booking = final_state.get("booking")

    # Format intents list for UI display
    raw_intents = final_state.get("intents") or {}
    intents_list = [k for k, v in raw_intents.items() if v is True]
    if raw_intents.get("extra_compensation_asks"):
        intents_list.extend(raw_intents["extra_compensation_asks"])

    # Extract policy cites for UI box
    policy_context = final_state.get("policy_context") or ""
    policy_cites = [line.strip() for line in policy_context.split("\n\n") if line.strip()]

    return ChatResponse(
        reply=resp_text,
        response=resp_text,
        pnr=body.pnr,
        customer_name=customer.get("name") if customer else None,
        actions=actions,
        actions_taken=actions,
        escalations=escalations_formatted,
        conversation_id=final_state.get("conversation_id"),
        customer_info=customer,
        booking_info=booking,
        intents=intents_list,
        policy_cites=policy_cites,
    )


@router.get("/conversations/{customer_id}", response_model=list[ConversationOut])
def get_conversations(
    customer_id: int,
    request: Request,
    _: None = Depends(require_auth),
    db=Depends(get_db),
):
    """Return all conversations for a given customer ID."""
    conversations = get_conversations_by_customer(customer_id, db)
    result = []
    for conv in conversations:
        turns = [
            ConversationTurnOut(id=t.id, role=t.role, content=t.content)
            for t in conv.turns
        ]
        action_logs = [
            {
                "id": al.id,
                "action_type": al.action_type,
                "details": al.details,
                "escalated": al.escalated,
            }
            for al in conv.action_logs
        ]
        result.append(
            ConversationOut(
                id=conv.id,
                customer_id=conv.customer_id,
                turns=turns,
                action_logs=action_logs,
            )
        )
    return result
