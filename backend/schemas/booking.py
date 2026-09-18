"""Pydantic schemas for booking data."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, field_validator


VALID_STATUSES = {"CANCELLED", "DELAYED", "ON_TIME"}


class BookingCreate(BaseModel):
    pnr: str
    customer_id: int
    flight_number: str
    route_origin: str
    route_dest: str
    flight_date: date
    scheduled_departure: datetime
    actual_departure: Optional[datetime] = None
    status: str
    delay_hours: Optional[float] = None

    @field_validator("scheduled_departure", mode="before")
    @classmethod
    def parse_scheduled_departure(cls, v: any) -> any:
        if isinstance(v, str) and len(v) == 5 and ":" in v:
            today_str = datetime.now().strftime("%Y-%m-%d")
            return f"{today_str}T{v}:00"
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v

    @field_validator("delay_hours")
    @classmethod
    def validate_delay(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("delay_hours must be non-negative")
        return v


class BookingOut(BaseModel):
    id: int
    pnr: str
    customer_id: int
    flight_number: str
    route_origin: str
    route_dest: str
    flight_date: date
    scheduled_departure: datetime
    actual_departure: Optional[datetime]
    status: str
    delay_hours: Optional[float]

    model_config = {"from_attributes": True}
