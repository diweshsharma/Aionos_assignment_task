"""Pydantic schemas for customer data."""

from typing import Optional
from pydantic import BaseModel, field_validator


VALID_TIERS = {"Gold", "Silver", "Platinum", "Standard"}


class CustomerCreate(BaseModel):
    name: str
    loyalty_tier: str
    contact: str
    flights_last_12mo: int = 0
    prior_complaints: list[dict] = []

    @field_validator("loyalty_tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        if v == "Base":
            return "Standard"
        if v not in VALID_TIERS:
            raise ValueError(f"loyalty_tier must be one of {VALID_TIERS}")
        return v


class CustomerOut(BaseModel):
    id: int
    name: str
    loyalty_tier: str
    contact: str
    flights_last_12mo: int
    prior_complaints: list[dict]

    model_config = {"from_attributes": True}
