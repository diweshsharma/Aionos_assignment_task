"""Pydantic schemas for chat API."""

from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    pnr: str
    message: str
    conversation_id: Optional[int] = None


class ActionDetail(BaseModel):
    type: str
    details: dict = {}


class ChatResponse(BaseModel):
    response: str
    actions: list[ActionDetail] = []
    escalations: list[str] = []
    conversation_id: Optional[int] = None


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
