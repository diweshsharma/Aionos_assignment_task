"""
Seed script — loads the 3 spec-mandated customers and their affected bookings.
Idempotent: skips any record whose PNR already exists in the DB.

Run directly:  python seed.py
Or called by:  main.py startup event
"""

from datetime import datetime, date

from database import SessionLocal, init_db
from models import Customer, Booking


SEED_CUSTOMERS = [
    {
        "name": "Priya Nair",
        "loyalty_tier": "Gold",
        "contact": "priya.nair@example.com",
        "flights_last_12mo": 6,
        "prior_complaints": [
            {"type": "delayed_baggage", "resolution": "voucher_issued", "resolved": True}
        ],
    },
    {
        "name": "Arvind Kulkarni",
        "loyalty_tier": "Silver",
        "contact": "arvind.kulkarni@example.com",
        "flights_last_12mo": 3,
        "prior_complaints": [],
    },
    {
        "name": "Meher Kaur",
        "loyalty_tier": "Platinum",
        "contact": "meher.kaur@example.com",
        "flights_last_12mo": 10,
        "prior_complaints": [
            {"type": "overbooking", "resolution": "tier_upgrade", "resolved": True}
        ],
    },
]

# Each entry maps to a customer by index (0-based)
SEED_BOOKINGS = [
    {
        "pnr": "SK4821X",
        "customer_index": 0,          # Priya Nair
        "flight_number": "SK-204",
        "route_origin": "Delhi",
        "route_dest": "Goa",
        "flight_date": date(2026, 9, 23),
        "scheduled_departure": datetime(2026, 9, 23, 8, 0),
        "actual_departure": None,
        "status": "CANCELLED",
        "delay_hours": None,
    },
    {
        "pnr": "TR1190B",
        "customer_index": 1,          # Arvind Kulkarni
        "flight_number": "SK-118",
        "route_origin": "Mumbai",
        "route_dest": "Bengaluru",
        "flight_date": date(2026, 9, 23),
        "scheduled_departure": datetime(2026, 9, 23, 7, 10),
        "actual_departure": datetime(2026, 9, 23, 11, 10),
        "status": "DELAYED",
        "delay_hours": 4.0,
    },
    {
        "pnr": "WL7742",
        "customer_index": 2,          # Meher Kaur
        "flight_number": "SK-305",
        "route_origin": "Delhi",
        "route_dest": "Hyderabad",
        "flight_date": date(2026, 9, 23),
        "scheduled_departure": datetime(2026, 9, 23, 14, 0),
        "actual_departure": datetime(2026, 9, 23, 20, 0),
        "status": "DELAYED",
        "delay_hours": 6.0,
    },
]


def seed_database() -> None:
    """Insert seed records if they are not already present."""
    init_db()
    db = SessionLocal()
    try:
        # Check if already seeded by looking for the first PNR
        existing = db.query(Booking).filter_by(pnr="SK4821X").first()
        if existing:
            print("[seed] Database already seeded — skipping.")
            return

        # Insert customers
        customer_records = []
        for c in SEED_CUSTOMERS:
            customer = Customer(
                name=c["name"],
                loyalty_tier=c["loyalty_tier"],
                contact=c["contact"],
                flights_last_12mo=c["flights_last_12mo"],
                prior_complaints=c["prior_complaints"],
            )
            db.add(customer)
            customer_records.append(customer)

        db.flush()  # assigns IDs before creating bookings

        # Insert bookings
        for b in SEED_BOOKINGS:
            customer = customer_records[b["customer_index"]]
            booking = Booking(
                pnr=b["pnr"],
                customer_id=customer.id,
                flight_number=b["flight_number"],
                route_origin=b["route_origin"],
                route_dest=b["route_dest"],
                flight_date=b["flight_date"],
                scheduled_departure=b["scheduled_departure"],
                actual_departure=b["actual_departure"],
                status=b["status"],
                delay_hours=b["delay_hours"],
            )
            db.add(booking)

        db.commit()
        print("[seed] Inserted 3 customers and 3 bookings successfully.")

    except Exception as exc:
        db.rollback()
        print(f"[seed] ERROR: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
