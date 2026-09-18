"""Pydantic schemas for chat API."""

from typing import Optional, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    pnr: str
    message: str
    conversation_id: Optional[int] = None


class ActionDetail(BaseModel):
    type: str
    details: dict = {}
    escalated: bool = False


class EscalationDetail(BaseModel):
    reason: str


class ChatResponse(BaseModel):
    reply: str
    response: str
    pnr: str = ""
    customer_name: Optional[str] = None
    actions: list[ActionDetail] = []
    actions_taken: list[ActionDetail] = []
    escalations: list[Any] = []
    conversation_id: Optional[int] = None
    customer_info: Optional[dict] = None
    booking_info: Optional[dict] = None
    intents: list[str] = []
    policy_cites: list[str] = []


class ConversationTurnOut(BaseModel):
    id: int
    role: str
    content: str

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: int
    customer_id: int
    turns: list[ConversationTurnOut] = []
    action_logs: list[dict] = []

    model_config = {"from_attributes": True}
