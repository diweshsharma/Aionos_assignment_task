from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from services.booking_service import get_customer_by_pnr

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PNRLookupRequest(BaseModel):
    pnr: str


class PNRLookupResponse(BaseModel):
    customer_id: int
    name: str
    loyalty_tier: str
    pnr: str
    contact: Optional[str] = None
    flights_last_12mo: int = 0
    prior_complaints: list[Any] = []
    booking: dict


@router.post("/token", response_model=TokenResponse)
def get_token(body: TokenRequest) -> TokenResponse:
    """
    Exchange the static secret token for a bearer token.
    In production this would be a real auth flow; for local deployment
    this is a simple secret-matching gate.
    """
    if body.token != settings.AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )
    return TokenResponse(access_token=settings.AUTH_TOKEN)


@router.post("/lookup-pnr", response_model=PNRLookupResponse)
def lookup_pnr(body: PNRLookupRequest, db: Session = Depends(get_db)) -> PNRLookupResponse:
    """
    Look up customer & booking details by PNR.
    Used by the login screen to validate a passenger before entering chat.
    """
    pnr_clean = body.pnr.strip().upper()
    result = get_customer_by_pnr(pnr_clean, db)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No booking found for PNR '{pnr_clean}'. Please check your PNR and try again.",
        )
    customer, booking = result
    return PNRLookupResponse(
        customer_id=customer.id,
        name=customer.name,
        loyalty_tier=customer.loyalty_tier,
        pnr=booking.pnr,
        contact=customer.contact,
        flights_last_12mo=customer.flights_last_12mo,
        prior_complaints=customer.prior_complaints or [],
        booking={
            "id": booking.id,
            "pnr": booking.pnr,
            "customer_id": booking.customer_id,
            "flight_number": booking.flight_number,
            "route_origin": booking.route_origin,
            "route_dest": booking.route_dest,
            "flight_date": str(booking.flight_date),
            "scheduled_departure": str(booking.scheduled_departure),
            "actual_departure": str(booking.actual_departure) if booking.actual_departure else None,
            "status": booking.status,
            "delay_hours": booking.delay_hours,
        },
    )
