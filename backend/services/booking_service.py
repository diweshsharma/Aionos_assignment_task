"""
Booking service — all customer/booking access goes through these functions.
No customer or booking data is hardcoded here; everything is read from the DB
so new records added via /admin/* are automatically visible.
"""

from typing import Optional
from sqlalchemy.orm import Session

from models import Customer, Booking, Conversation, ConversationTurn, ActionLog


# ── Lookup helpers ────────────────────────────────────────────────────────────

def get_customer_by_pnr(
    pnr: str, db: Session
) -> Optional[tuple[Customer, Booking]]:
    """
    Look up a customer via their PNR.  Returns the Customer and the
    most-relevant Booking (preferring CANCELLED/DELAYED over ON_TIME).
    Returns None if the PNR is not found.
    """
    bookings = db.query(Booking).filter(Booking.pnr == pnr).all()
    if not bookings:
        return None

    customer = db.query(Customer).filter(
        Customer.id == bookings[0].customer_id
    ).first()
    if not customer:
        return None

    # Prefer the affected flight (CANCELLED / DELAYED) over ON_TIME
    _priority = {"CANCELLED": 0, "DELAYED": 1, "ON_TIME": 2}
    bookings_sorted = sorted(
        bookings, key=lambda b: _priority.get(str(b.status), 99)
    )
    return customer, bookings_sorted[0]


def get_customer_by_id(customer_id: int, db: Session) -> Optional[Customer]:
    return db.query(Customer).filter(Customer.id == customer_id).first()


def get_bookings_for_customer(customer_id: int, db: Session) -> list[Booking]:
    return db.query(Booking).filter(Booking.customer_id == customer_id).all()


# ── Create helpers (used by /admin endpoints) ─────────────────────────────────

def create_customer(data: dict, db: Session) -> Customer:
    customer = Customer(
        name=data["name"],
        loyalty_tier=data["loyalty_tier"],
        contact=data["contact"],
        flights_last_12mo=data.get("flights_last_12mo", 0),
        prior_complaints=data.get("prior_complaints", []),
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def create_booking(data: dict, db: Session) -> Booking:
    booking = Booking(
        pnr=data["pnr"],
        customer_id=data["customer_id"],
        flight_number=data["flight_number"],
        route_origin=data["route_origin"],
        route_dest=data["route_dest"],
        flight_date=data["flight_date"],
        scheduled_departure=data["scheduled_departure"],
        actual_departure=data.get("actual_departure"),
        status=data["status"],
        delay_hours=data.get("delay_hours"),
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


# ── Conversation helpers ───────────────────────────────────────────────────────

def get_or_create_conversation(customer_id: int, db: Session) -> Conversation:
    """Start a fresh conversation each time (not resuming old ones by default)."""
    conv = Conversation(customer_id=customer_id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_conversation(conversation_id: int, db: Session) -> Optional[Conversation]:
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def get_conversations_by_customer(
    customer_id: int, db: Session
) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.customer_id == customer_id)
        .order_by(Conversation.id.desc())
        .all()
    )


def log_turn(
    conversation_id: int,
    role: str,
    content: str,
    db: Session,
) -> ConversationTurn:
    turn = ConversationTurn(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )
    db.add(turn)
    db.commit()
    db.refresh(turn)
    return turn


def log_action(
    conversation_id: int,
    action_type: str,
    details: dict,
    escalated: bool,
    db: Session,
) -> ActionLog:
    record = ActionLog(
        conversation_id=conversation_id,
        action_type=action_type,
        details=details,
        escalated=escalated,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
