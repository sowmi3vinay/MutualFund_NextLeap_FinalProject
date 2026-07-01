import os
import threading
from pathlib import Path

from dotenv import load_dotenv

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_PROVIDER = "sentence-transformers"
EMBEDDING_DIMENSIONS = 384
DEFAULT_EMBEDDING_BATCH_SIZE = 32

_MODEL = None
_MODEL_LOCK = threading.RLock()


def _load_environment():
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(project_root / ".env")


def get_embedding_model():
    global _MODEL
    _load_environment()
    with _MODEL_LOCK:
        if _MODEL is None:
            from sentence_transformers import SentenceTransformer

            local_files_only = os.getenv("EMBEDDING_LOCAL_FILES_ONLY", "true").lower() == "true"
            if local_files_only:
                os.environ.setdefault("HF_HUB_OFFLINE", "1")
                os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

            load_attempts = [
                {"local_files_only": local_files_only},
                {
                    "local_files_only": local_files_only,
                    "device": "cpu",
                    "model_kwargs": {"low_cpu_mem_usage": False},
                },
            ]
            last_error = None
            for kwargs in load_attempts:
                try:
                    _MODEL = SentenceTransformer(EMBEDDING_MODEL, **kwargs)
                    break
                except Exception as exc:
                    last_error = exc
                    _MODEL = None

            if _MODEL is None and last_error is not None:
                raise last_error
    return _MODEL


def embed_texts(texts, batch_size=DEFAULT_EMBEDDING_BATCH_SIZE):
    cleaned_texts = [text.strip() for text in texts if text and text.strip()]
    if not cleaned_texts:
        return []

    model = get_embedding_model()
    embeddings = model.encode(
        cleaned_texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embeddings.tolist()


def embed_query(query):
    embeddings = embed_texts([query])
    if not embeddings:
        raise ValueError("Query must not be empty.")
    return embeddings[0]
