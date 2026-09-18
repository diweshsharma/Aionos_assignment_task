"""SQLAlchemy ORM models for all persisted entities."""

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Float,
    Boolean, JSON, ForeignKey, Text, func,
)
from sqlalchemy.orm import relationship

from database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    loyalty_tier = Column(String(50), nullable=False)   # Gold / Silver / Platinum / Standard
    contact = Column(String(200), nullable=False)
    flights_last_12mo = Column(Integer, default=0)
    prior_complaints = Column(JSON, default=list)        # list[dict]
    created_at = Column(DateTime, default=func.now())

    bookings = relationship("Booking", back_populates="customer")
    conversations = relationship("Conversation", back_populates="customer")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    pnr = Column(String(20), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    flight_number = Column(String(20), nullable=False)
    route_origin = Column(String(100), nullable=False)
    route_dest = Column(String(100), nullable=False)
    flight_date = Column(Date, nullable=False)
    scheduled_departure = Column(DateTime, nullable=False)
    actual_departure = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)         # CANCELLED / DELAYED / ON_TIME
    delay_hours = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())

    customer = relationship("Customer", back_populates="bookings")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    started_at = Column(DateTime, default=func.now())

    customer = relationship("Customer", back_populates="conversations")
    turns = relationship("ConversationTurn", back_populates="conversation", order_by="ConversationTurn.id")
    action_logs = relationship("ActionLog", back_populates="conversation")


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)           # "user" or "agent"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())

    conversation = relationship("Conversation", back_populates="turns")


class ActionLog(Base):
    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    action_type = Column(String(100), nullable=False)   # e.g. "meal_voucher_issued"
    details = Column(JSON, default=dict)                # action-specific payload
    escalated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    conversation = relationship("Conversation", back_populates="action_logs")
