"""
core/config.py — centralised configuration via environment variables.
Copy .env.example → .env and fill in your secrets.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # ── Telegram ─────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN")

    # ── LLM (Anthropic Claude) ────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str  = os.getenv("ANTHROPIC_API_KEY")
    LLM_MODEL: str          = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
    LLM_MAX_TOKENS: int     = int(os.getenv("LLM_MAX_TOKENS", "1024"))

    # ── Embeddings ────────────────────────────────────────────────────────────
    # Swap for OpenAI / Cohere / local model as needed
    EMBEDDING_MODEL: str    = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    OPENAI_API_KEY: str     = os.getenv("OPENAI_API_KEY", "")

    # ── Vector store ──────────────────────────────────────────────────────────
    VECTOR_STORE_PATH: str  = os.getenv("VECTOR_STORE_PATH", "data/vectorstore")
    TOP_K_RESULTS: int      = int(os.getenv("TOP_K_RESULTS", "4"))

    # ── Documents ─────────────────────────────────────────────────────────────
    DOCS_PATH: str          = os.getenv("DOCS_PATH", "data/docs")
