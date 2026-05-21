"""
core/rag.py — RAG pipeline skeleton.

Swap the stub classes for your real implementations:
  - Embedder   → OpenAI / HuggingFace / Cohere / local
  - VectorStore → FAISS / Chroma / Pinecone / Weaviate
  - DocumentLoader → PDF / CSV / web scrape / DB query
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import List

import anthropic

from core.config import Config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Document loader
# ─────────────────────────────────────────────────────────────────────────────

class DocumentLoader:
    """Load raw documents from a directory (txt/md files by default)."""

    def __init__(self, docs_path: str):
        self.docs_path = Path(docs_path)

    def load(self) -> List[dict]:
        """
        Returns a list of {"id": str, "text": str, "metadata": dict} dicts.
        Replace with your own source (PDFs, DB, API, …).
        """
        documents = []
        if not self.docs_path.exists():
            logger.warning("Docs path %s not found — returning empty corpus.", self.docs_path)
            return documents

        for path in self.docs_path.rglob("*.txt"):
            text = path.read_text(encoding="utf-8")
            documents.append({
                "id": str(path),
                "text": text,
                "metadata": {"source": str(path)},
            })

        logger.info("Loaded %d documents from %s", len(documents), self.docs_path)
        return documents


# ─────────────────────────────────────────────────────────────────────────────
# 2. Embedder stub
# ─────────────────────────────────────────────────────────────────────────────

class Embedder:
    """
    Thin wrapper around an embedding model.
    Default stub: replace with openai / sentence-transformers / etc.
    """

    def __init__(self, model: str = "text-embedding-3-small", api_key: str = ""):
        self.model = model
        self.api_key = api_key
        # e.g. self.client = openai.OpenAI(api_key=api_key)

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Return a list of embedding vectors (one per text)."""
        # ── STUB ──────────────────────────────────────────────────────────────
        # Replace with real call, e.g.:
        #   response = self.client.embeddings.create(input=texts, model=self.model)
        #   return [d.embedding for d in response.data]
        raise NotImplementedError("Plug in your embedding model here.")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Vector store stub
# ─────────────────────────────────────────────────────────────────────────────

class VectorStore:
    """
    Simple wrapper around a vector database.
    Default stub: replace with FAISS / Chroma / Pinecone / Weaviate.
    """

    def __init__(self, store_path: str, embedder: Embedder):
        self.store_path = store_path
        self.embedder = embedder
        self._store = None   # lazy-init

    def build(self, documents: List[dict]) -> None:
        """Embed documents and persist the index."""
        texts = [d["text"] for d in documents]
        # vectors = self.embedder.embed(texts)
        # self._store = YourVectorDB.from_embeddings(texts, vectors)
        # self._store.save(self.store_path)
        logger.info("Vector store built with %d documents (stub — not persisted).", len(documents))

    def load(self) -> None:
        """Load a previously persisted index from disk."""
        # self._store = YourVectorDB.load(self.store_path)
        logger.info("Vector store loaded from %s (stub).", self.store_path)

    def search(self, query: str, top_k: int = 4) -> List[dict]:
        """
        Return the top-k most relevant document chunks.
        Each result: {"text": str, "score": float, "metadata": dict}
        """
        # query_vec = self.embedder.embed([query])[0]
        # results   = self._store.search(query_vec, top_k)
        # return results

        # ── STUB — returns empty list ──────────────────────────────────────────
        logger.warning("VectorStore.search() is a stub — returning no context.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# 4. RAG pipeline
# ─────────────────────────────────────────────────────────────────────────────

class RAGPipeline:
    """
    Orchestrates: query → retrieve → augment → generate.
    """

    SYSTEM_PROMPT = (
        "You are a helpful assistant. "
        "Answer the user's question using ONLY the context provided below. "
        "If the context does not contain enough information, say so honestly.\n\n"
        "Context:\n{context}"
    )

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.client = anthropic.Anthropic(api_key=cfg.ANTHROPIC_API_KEY)

        self.embedder = Embedder(model=cfg.EMBEDDING_MODEL, api_key=cfg.OPENAI_API_KEY)
        self.store    = VectorStore(store_path=cfg.VECTOR_STORE_PATH, embedder=self.embedder)

    # ── Initialisation helpers ────────────────────────────────────────────────

    def build_index(self) -> None:
        """Call once to (re)build the vector index from raw documents."""
        loader = DocumentLoader(self.cfg.DOCS_PATH)
        docs   = loader.load()
        self.store.build(docs)

    def load_index(self) -> None:
        """Call on startup to load an already-built index."""
        self.store.load()

    # ── Main query method ─────────────────────────────────────────────────────

    def query(self, user_message: str) -> str:
        """
        Full RAG turn:
          1. Retrieve relevant chunks from the vector store.
          2. Build an augmented prompt.
          3. Call Claude and return the response text.
        """
        # 1. Retrieve
        hits    = self.store.search(user_message, top_k=self.cfg.TOP_K_RESULTS)
        context = "\n\n---\n\n".join(h["text"] for h in hits) if hits else "No context found."

        # 2. Build system prompt
        system = self.SYSTEM_PROMPT.format(context=context)

        # 3. Generate
        response = self.client.messages.create(
            model      = self.cfg.LLM_MODEL,
            max_tokens = self.cfg.LLM_MAX_TOKENS,
            system     = system,
            messages   = [{"role": "user", "content": user_message}],
        )

        return response.content[0].text
