import os
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_VECTOR_BACKEND = "chroma"


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
    backend = vector_backend()
    if backend == "supabase":
        from services.supabase_vector_store import SupabaseVectorStore

        return SupabaseVectorStore()
    if backend == "chroma":
        from services.chroma_vector_store import ChromaVectorStore

        return ChromaVectorStore()
    raise ValueError(f"Unsupported VECTOR_BACKEND: {backend}")
