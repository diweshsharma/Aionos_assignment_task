"""
FastAPI application entry point.

Startup sequence:
  1. Create DB tables
  2. Seed 3 initial customers/bookings (idempotent)
  3. Initialize Chroma RAG from policy_rules.yaml
  4. Build LangGraph agent graph
  5. Mount routers
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, SessionLocal
from seed import seed_database
from services.policy_engine import policy_engine
from services.rag_service import initialize_rag, rag_service
from services.llm_client import LLMClient
from agent.graph import create_graph
from routers import auth, chat, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== Airline Disruption Agent starting up ===")

    # 1. DB tables
    init_db()
    logger.info("[startup] DB tables ensured.")

    # 2. Seed data
    seed_database()

    # 3. Policy engine (loads YAML)
    logger.info("[startup] Policy engine loaded from %s", policy_engine._yaml_path)

    # 4. Chroma RAG
    initialize_rag(policy_engine)
    logger.info("[startup] Chroma RAG indexed.")

    # 5. LLM client
    llm = LLMClient()

    # 6. Build LangGraph graph
    graph = create_graph(llm, policy_engine, rag_service, SessionLocal)
    app.state.graph = graph
    logger.info("[startup] LangGraph agent compiled.")

    logger.info("=== Startup complete. Listening on http://0.0.0.0:8000 ===")
    yield
    logger.info("=== Airline Disruption Agent shutting down ===")


app = FastAPI(
    title="Airline Disruption Resolution Agent",
    description=(
        "AI agent handling flight cancellation / delay support. "
        "Policy decisions are driven by policy_rules.yaml, never by raw LLM judgment."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (frontend Vite dev server on port 5173) ──────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(admin.router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "airline-disruption-agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
