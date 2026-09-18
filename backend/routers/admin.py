"""
Admin router — data ingestion endpoints for adding customers and bookings
without code changes.  All three endpoints require the same bearer token.

POST /admin/customers  — single customer record
POST /admin/bookings   — single booking record
POST /admin/import     — CSV bulk upload (customers_csv and/or bookings_csv)
"""

from __future__ import annotations

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from database import get_db
from schemas.customer import CustomerCreate, CustomerOut
from schemas.booking import BookingCreate, BookingOut
from services.booking_service import create_customer, create_booking
from routers.deps import require_auth

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Single-record endpoints ───────────────────────────────────────────────────

@router.post(
    "/customers",
    response_model=CustomerOut,
    status_code=status.HTTP_201_CREATED,
)
def add_customer(
    body: CustomerCreate,
    _: None = Depends(require_auth),
    db=Depends(get_db),
):
    """Insert a single new customer record."""
    customer = create_customer(body.model_dump(), db)
    return customer


@router.post(
    "/bookings",
    response_model=BookingOut,
    status_code=status.HTTP_201_CREATED,
)
def add_booking(
    body: BookingCreate,
    _: None = Depends(require_auth),
    db=Depends(get_db),
):
    """Insert a single new booking record."""
    booking = create_booking(body.model_dump(), db)
    return booking


# ── CSV bulk import ───────────────────────────────────────────────────────────

def _parse_customers_csv(content: bytes) -> tuple[list[CustomerCreate], list[dict]]:
    """
    Parse a customers CSV file.
    Returns (valid_rows, failures).
    Failures: list of {"row": int, "error": str}.
    """
    valid: list[CustomerCreate] = []
    failures: list[dict] = []
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    for i, row in enumerate(reader, start=2):  # row 1 is header
        try:
            # Coerce prior_complaints — expect JSON string or empty
            import json as _json
            prior = row.get("prior_complaints", "[]") or "[]"
            try:
                prior_parsed = _json.loads(prior)
            except Exception:
                prior_parsed = []
            obj = CustomerCreate(
                name=row["name"],
                loyalty_tier=row["loyalty_tier"],
                contact=row["contact"],
                flights_last_12mo=int(row.get("flights_last_12mo", 0)),
                prior_complaints=prior_parsed,
            )
            valid.append(obj)
        except Exception as exc:
            failures.append({"row": i, "error": str(exc), "data": dict(row)})
    return valid, failures


def _parse_bookings_csv(content: bytes) -> tuple[list[BookingCreate], list[dict]]:
    """
    Parse a bookings CSV file.
    Returns (valid_rows, failures).
    """
    from datetime import date, datetime
    valid: list[BookingCreate] = []
    failures: list[dict] = []
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    for i, row in enumerate(reader, start=2):
        try:
            delay_h = row.get("delay_hours") or None
            obj = BookingCreate(
                pnr=row["pnr"],
                customer_id=int(row["customer_id"]),
                flight_number=row["flight_number"],
                route_origin=row["route_origin"],
                route_dest=row["route_dest"],
                flight_date=date.fromisoformat(row["flight_date"]),
                scheduled_departure=datetime.fromisoformat(row["scheduled_departure"]),
                actual_departure=datetime.fromisoformat(row["actual_departure"]) if row.get("actual_departure") else None,
                status=row["status"],
                delay_hours=float(delay_h) if delay_h else None,
            )
            valid.append(obj)
        except Exception as exc:
            failures.append({"row": i, "error": str(exc), "data": dict(row)})
    return valid, failures


@router.post("/import")
async def bulk_import(
    _: None = Depends(require_auth),
    db=Depends(get_db),
    customers_csv: Optional[UploadFile] = File(None),
    bookings_csv: Optional[UploadFile] = File(None),
):
    """
    Bulk CSV import.  Accepts one or both CSV files.

    Validation rules:
    - ALL rows in a file must be valid before ANY are inserted (atomic per file).
    - Returns a per-file success/failure report.
    - Never silently commits a malformed batch.
    """
    if not customers_csv and not bookings_csv:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one of customers_csv or bookings_csv must be provided.",
        )

    report: dict = {}

    # ── Customers CSV ─────────────────────────────────────────────────────────
    if customers_csv:
        content = await customers_csv.read()
        valid_customers, cust_failures = _parse_customers_csv(content)

        if cust_failures:
            report["customers"] = {
                "status": "rejected",
                "total_rows": len(valid_customers) + len(cust_failures),
                "success_count": 0,
                "failure_count": len(cust_failures),
                "failures": cust_failures,
                "message": "No records were inserted. Fix all errors and re-upload.",
            }
        else:
            inserted = []
            try:
                for c in valid_customers:
                    record = create_customer(c.model_dump(), db)
                    inserted.append(record.id)
                report["customers"] = {
                    "status": "success",
                    "total_rows": len(valid_customers),
                    "success_count": len(inserted),
                    "failure_count": 0,
                    "inserted_ids": inserted,
                }
            except Exception as exc:
                db.rollback()
                report["customers"] = {
                    "status": "error",
                    "message": str(exc),
                    "success_count": 0,
                    "failure_count": len(valid_customers),
                }

    # ── Bookings CSV ──────────────────────────────────────────────────────────
    if bookings_csv:
        content = await bookings_csv.read()
        valid_bookings, book_failures = _parse_bookings_csv(content)

        if book_failures:
            report["bookings"] = {
                "status": "rejected",
                "total_rows": len(valid_bookings) + len(book_failures),
                "success_count": 0,
                "failure_count": len(book_failures),
                "failures": book_failures,
                "message": "No records were inserted. Fix all errors and re-upload.",
            }
        else:
            inserted = []
            try:
                for b in valid_bookings:
                    booking_record = create_booking(b.model_dump(), db)
                    inserted.append(booking_record.id)
                report["bookings"] = {
                    "status": "success",
                    "total_rows": len(valid_bookings),
                    "success_count": len(inserted),
                    "failure_count": 0,
                    "inserted_ids": inserted,
                }
            except Exception as exc:
                db.rollback()
                report["bookings"] = {
                    "status": "error",
                    "message": str(exc),
                    "success_count": 0,
                    "failure_count": len(valid_bookings),
                }

    return report
