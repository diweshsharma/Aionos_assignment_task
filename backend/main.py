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

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(admin.router)

# ── Serve static frontend dist if present ──────────────────────────────────────
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api") or full_path in ["health", "docs", "openapi.json"]:
            return None
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))


@app.get("/")
def root():
    return {
        "service": "AIONOS SkyAssist API",
        "status": "online",
        "docs": "/docs",
        "health": "/health",
    }


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "airline-disruption-agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
