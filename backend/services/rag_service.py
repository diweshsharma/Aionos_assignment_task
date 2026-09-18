"""
RAG service — indexes policy documents into a persistent Chroma collection
using local sentence-transformers embeddings (no API cost).

The collection is seeded/upserted from policy_engine.generate_policy_documents()
on every startup so it always mirrors the current policy_rules.yaml.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class RAGService:
    """Wraps a Chroma collection for policy document retrieval."""

    def __init__(
        self,
        chroma_path: Optional[str] = None,
        collection_name: str = "airline_policy",
    ) -> None:
        from config import settings
        import chromadb
        from chromadb.utils import embedding_functions

        self._chroma_path = chroma_path or settings.CHROMA_PATH
        self._collection_name = collection_name

        Path(self._chroma_path).mkdir(parents=True, exist_ok=True)

        self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self._client = chromadb.PersistentClient(path=self._chroma_path)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=self._ef,  # type: ignore[arg-type]
            metadata={"hnsw:space": "cosine"},
        )

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index_policy(self, documents: list[str]) -> None:
        """
        Upsert all policy documents.  Safe to call on every startup —
        existing embeddings are reused from the persistent store.
        """
        ids = [f"policy_doc_{i}" for i in range(len(documents))]
        self._collection.upsert(documents=documents, ids=ids)
        logger.info("[RAG] Indexed %d policy documents into Chroma.", len(documents))

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(self, query: str, n_results: int = 3) -> str:
        """
        Query the collection and return the top-n documents joined as a
        single context string.
        """
        count = self._collection.count()
        if count == 0:
            return "No policy documents available."

        actual_n = min(n_results, count)
        results = self._collection.query(
            query_texts=[query],
            n_results=actual_n,
        )
        documents = results.get("documents")
        if documents and len(documents) > 0:
            docs = documents[0]
            return "\n\n".join(docs) if docs else ""
        return ""

    @property
    def doc_count(self) -> int:
        return self._collection.count()


# ── Module-level singleton ────────────────────────────────────────────────────

_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Lazy singleton — only instantiated on first call."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


# For convenience, expose as rag_service attribute but lazily initialized
class _LazyRAGProxy:
    """Proxy that initializes RAGService on first attribute access."""
    _instance: Optional[RAGService] = None

    def _get(self) -> RAGService:
        if self._instance is None:
            self._instance = RAGService()
        return self._instance

    def retrieve(self, *args, **kwargs):
        return self._get().retrieve(*args, **kwargs)

    def index_policy(self, *args, **kwargs):
        return self._get().index_policy(*args, **kwargs)

    @property
    def doc_count(self):
        return self._get().doc_count


rag_service = _LazyRAGProxy()


def initialize_rag(policy_engine) -> None:
    """
    Called at app startup.  Generates policy documents from the loaded YAML
    and upserts them into the persistent Chroma collection.
    """
    docs = policy_engine.generate_policy_documents()
    rag_service.index_policy(docs)
