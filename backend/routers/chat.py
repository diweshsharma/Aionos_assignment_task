"""
Chat router — POST /chat and GET /conversations/{customer_id}.

The LangGraph compiled graph and services are loaded at app startup and
injected via FastAPI's app.state so they are not re-created per request.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from database import get_db
from schemas.chat import ChatRequest, ChatResponse, ActionDetail, ConversationOut, ConversationTurnOut
from services.booking_service import get_conversations_by_customer, get_customer_by_pnr
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
    Main chat endpoint.  Invokes the LangGraph agent and returns the response,
    the list of actions taken, and any escalation reasons.
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
        ActionDetail(type=a["type"], details=a.get("details", {}))
        for a in final_state.get("actions_taken", [])
    ]

    return ChatResponse(
        response=final_state.get("response") or "No response generated.",
        actions=actions,
        escalations=final_state.get("escalations", []),
        conversation_id=final_state.get("conversation_id"),
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
