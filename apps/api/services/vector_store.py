import os
import threading
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_VECTOR_BACKEND = "chroma"
_VECTOR_STORE = None
_VECTOR_STORE_LOCK = threading.RLock()


class VectorStore(Protocol):
    def add_chunks(self, chunks):
        ...

    def search(self, query_embedding, top_k=5):
        ...

    def count(self):
        ...


def _load_environment():
    load_dotenv(PROJECT_ROOT / ".env")


def vector_backend():
    _load_environment()
    return os.getenv("VECTOR_BACKEND", DEFAULT_VECTOR_BACKEND).strip().lower()


def get_vector_store() -> VectorStore:
    global _VECTOR_STORE
    with _VECTOR_STORE_LOCK:
        if _VECTOR_STORE is not None:
            return _VECTOR_STORE

        backend = vector_backend()
        if backend == "supabase":
            from services.supabase_vector_store import SupabaseVectorStore

            _VECTOR_STORE = SupabaseVectorStore()
        elif backend == "chroma":
            from services.chroma_vector_store import ChromaVectorStore

            _VECTOR_STORE = ChromaVectorStore()
        else:
            raise ValueError(f"Unsupported VECTOR_BACKEND: {backend}")
    return _VECTOR_STORE
