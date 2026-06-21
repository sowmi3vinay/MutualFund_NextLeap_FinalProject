import json
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_DIR = PROJECT_ROOT / "apps" / "api"
sys.path.insert(0, str(API_DIR))

from services.embedding_service import EMBEDDING_MODEL, embed_texts  # noqa: E402
from services.vector_store import get_vector_store, vector_backend  # noqa: E402

CHUNKS_PATH = PROJECT_ROOT / "data" / "sources" / "processed" / "source_chunks.jsonl"


def load_chunks():
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            f"Missing chunks file: {CHUNKS_PATH}. Run scripts/ingest_sources.py first."
        )

    chunks = []
    with CHUNKS_PATH.open(encoding="utf-8") as chunks_file:
        for line in chunks_file:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def refresh_vector_store():
    load_dotenv(PROJECT_ROOT / ".env")
    chunks = load_chunks()
    documents = [chunk["text"] for chunk in chunks]
    embeddings = embed_texts(documents)
    embedded_chunks = [
        {
            **chunk,
            "embedding": embeddings[index],
        }
        for index, chunk in enumerate(chunks)
    ]

    vector_store = get_vector_store()
    stored_count = vector_store.add_chunks(embedded_chunks)

    print(f"Stored {stored_count} chunks using VECTOR_BACKEND={vector_backend()}")
    print(f"Embedding model: {EMBEDDING_MODEL}")


if __name__ == "__main__":
    refresh_vector_store()
