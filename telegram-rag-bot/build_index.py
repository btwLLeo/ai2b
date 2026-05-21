"""
build_index.py — run this once (or on a schedule) to (re)build the vector store.

Usage:
    python build_index.py
"""
import logging
from core.config import Config
from core.rag import RAGPipeline

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

if __name__ == "__main__":
    cfg      = Config()
    pipeline = RAGPipeline(cfg)
    pipeline.build_index()
    print("✅ Index built successfully.")
