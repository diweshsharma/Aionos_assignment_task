"""
Pytest fixtures shared across all test modules.

Uses a shared SQLite in-memory database (via a persistent connection)
so that seed data written by one fixture session is visible to graph nodes
that open fresh sessions on the same engine.

The LLM is always mocked — no network calls in tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from models import Customer, Booking
from services.policy_engine import PolicyEngine
from services.llm_client import MockLLMClient
from services.rag_service import RAGService

# ── Per-test SQLite file DB (isolates tests while letting multiple sessions share) ─

@pytest.fixture(scope="function")
def test_engine(tmp_path):
    db_path = tmp_path / "test_airline.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def TestSessionLocal(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db(TestSessionLocal):
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── Seed 3 canonical customers into the test DB ──────────────────────────────

@pytest.fixture(scope="function")
def seeded_db(db):
    """Insert the 3 spec-mandated customers and bookings into the test DB."""
    from datetime import datetime, date

    priya = Customer(
        name="Priya Nair",
        loyalty_tier="Gold",
        contact="priya.nair@example.com",
        flights_last_12mo=6,
        prior_complaints=[{"type": "delayed_baggage", "resolution": "voucher_issued"}],
    )
    arvind = Customer(
        name="Arvind Kulkarni",
        loyalty_tier="Silver",
        contact="arvind.kulkarni@example.com",
        flights_last_12mo=3,
        prior_complaints=[],
    )
    meher = Customer(
        name="Meher Kaur",
        loyalty_tier="Platinum",
        contact="meher.kaur@example.com",
        flights_last_12mo=10,
        prior_complaints=[{"type": "overbooking", "resolution": "tier_upgrade"}],
    )
    db.add_all([priya, arvind, meher])
    db.flush()

    db.add(Booking(
        pnr="SK4821X", customer_id=priya.id,
        flight_number="SK-204", route_origin="Delhi", route_dest="Goa",
        flight_date=date(2026, 9, 23), scheduled_departure=datetime(2026, 9, 23, 8, 0),
        actual_departure=None, status="CANCELLED", delay_hours=None,
    ))
    db.add(Booking(
        pnr="TR1190B", customer_id=arvind.id,
        flight_number="SK-118", route_origin="Mumbai", route_dest="Bengaluru",
        flight_date=date(2026, 9, 23), scheduled_departure=datetime(2026, 9, 23, 7, 10),
        actual_departure=datetime(2026, 9, 23, 11, 10), status="DELAYED", delay_hours=4.0,
    ))
    db.add(Booking(
        pnr="WL7742", customer_id=meher.id,
        flight_number="SK-305", route_origin="Delhi", route_dest="Hyderabad",
        flight_date=date(2026, 9, 23), scheduled_departure=datetime(2026, 9, 23, 14, 0),
        actual_departure=datetime(2026, 9, 23, 20, 0), status="DELAYED", delay_hours=6.0,
    ))
    db.commit()
    db.refresh(priya); db.refresh(arvind); db.refresh(meher)
    return db, priya, arvind, meher


# ── Policy engine pointing at the real YAML ───────────────────────────────────

@pytest.fixture(scope="session")
def policy():
    return PolicyEngine()


# ── RAG service (in-memory Chroma, not persistent) ────────────────────────────

@pytest.fixture(scope="session")
def rag(policy, tmp_path_factory):
    tmp = str(tmp_path_factory.mktemp("chroma"))
    svc = RAGService(chroma_path=tmp)
    svc.index_policy(policy.generate_policy_documents())
    return svc


# ── FastAPI test client ───────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def client(TestSessionLocal, policy, rag):
    """
    Create a TestClient with:
      - Per-test file SQLite DB (TestSessionLocal)
      - Real policy engine
      - In-memory Chroma RAG
      - MockLLMClient (no Groq API calls)
      - Startup event bypassed (seeding + Chroma already done by fixtures)
    """
    from main import app
    from agent.graph import create_graph

    mock_llm = MockLLMClient(response_text="Test agent response.")
    graph = create_graph(mock_llm, policy, rag, TestSessionLocal)
    app.state.graph = graph

    # Override DB dependency so routes use the test DB
    def override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    # Seed the test DB with the 3 canonical records
    _seed_test_db(TestSessionLocal)

    # Use raise_server_exceptions=True so test errors surface cleanly.
    # app_state.graph is already set so startup event does not need to run.
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()



# ── Seed helper (used by client fixture) ─────────────────────────────────────

def _seed_test_db(SessionLocal) -> None:
    """Insert the 3 spec-mandated customers and bookings into the test DB."""
    from datetime import datetime, date
    db = SessionLocal()
    try:
        priya = Customer(name="Priya Nair", loyalty_tier="Gold",
            contact="priya.nair@example.com", flights_last_12mo=6,
            prior_complaints=[{"type": "delayed_baggage"}])
        arvind = Customer(name="Arvind Kulkarni", loyalty_tier="Silver",
            contact="arvind.kulkarni@example.com", flights_last_12mo=3,
            prior_complaints=[])
        meher = Customer(name="Meher Kaur", loyalty_tier="Platinum",
            contact="meher.kaur@example.com", flights_last_12mo=10,
            prior_complaints=[{"type": "overbooking"}])
        db.add_all([priya, arvind, meher])
        db.flush()
        db.add(Booking(pnr="SK4821X", customer_id=priya.id,
            flight_number="SK-204", route_origin="Delhi", route_dest="Goa",
            flight_date=date(2026, 9, 23), scheduled_departure=datetime(2026, 9, 23, 8, 0),
            actual_departure=None, status="CANCELLED", delay_hours=None))
        db.add(Booking(pnr="TR1190B", customer_id=arvind.id,
            flight_number="SK-118", route_origin="Mumbai", route_dest="Bengaluru",
            flight_date=date(2026, 9, 23), scheduled_departure=datetime(2026, 9, 23, 7, 10),
            actual_departure=datetime(2026, 9, 23, 11, 10), status="DELAYED", delay_hours=4.0))
        db.add(Booking(pnr="WL7742", customer_id=meher.id,
            flight_number="SK-305", route_origin="Delhi", route_dest="Hyderabad",
            flight_date=date(2026, 9, 23), scheduled_departure=datetime(2026, 9, 23, 14, 0),
            actual_departure=datetime(2026, 9, 23, 20, 0), status="DELAYED", delay_hours=6.0))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# ── Auth header helper ────────────────────────────────────────────────────────

@pytest.fixture
def auth_headers():
    from config import settings
    return {"Authorization": f"Bearer {settings.AUTH_TOKEN}"}


# ── LangGraph integration helper ──────────────────────────────────────────────

def make_graph(mock_llm, policy, rag, SessionLocal):
    """Helper to create a graph with injected mocks."""
    from agent.graph import create_graph
    return create_graph(mock_llm, policy, rag, SessionLocal)


def invoke_graph(graph, pnr: str, message: str, conversation_id=None) -> dict:
    """Invoke the graph with a minimal initial state and return final state."""
    initial = {
        "pnr": pnr,
        "message": message,
        "conversation_id": conversation_id,
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
    return graph.invoke(initial)
