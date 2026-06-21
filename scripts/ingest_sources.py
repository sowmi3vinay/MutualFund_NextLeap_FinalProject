import csv
import io
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_DIR = PROJECT_ROOT / "apps" / "api"
sys.path.insert(0, str(API_DIR))

from services.embedding_service import EMBEDDING_MODEL, embed_texts  # noqa: E402
from services.vector_store import get_vector_store, vector_backend  # noqa: E402

MANIFEST_PATH = PROJECT_ROOT / "data" / "sources" / "source_manifest.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "sources" / "processed"
CHUNKS_PATH = PROCESSED_DIR / "source_chunks.jsonl"
MIN_CHUNK_CHARS = 500
MAX_CHUNK_CHARS = 1000
CHUNK_OVERLAP_CHARS = 150
REQUEST_TIMEOUT_SECONDS = 30


def load_manifest():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Missing source manifest: {MANIFEST_PATH}")

    with MANIFEST_PATH.open(newline="", encoding="utf-8") as manifest_file:
        reader = csv.DictReader(manifest_file)
        return [row for row in reader if row.get("source_id") and row.get("url")]


def fetch_url(url):
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={
            "User-Agent": "MutualFundAdvisorSuite/0.1 (+https://localhost)",
        },
    )
    response.raise_for_status()
    return response.content, response.headers.get("content-type", "")


def extract_pdf_text(content):
    reader = PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def extract_html_text(content):
    soup = BeautifulSoup(content, "html.parser")
    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()
    return soup.get_text(separator="\n")


def extract_text(url, content, content_type):
    parsed_path = urlparse(url).path.lower()
    if "pdf" in content_type.lower() or parsed_path.endswith(".pdf"):
        return extract_pdf_text(content)
    return extract_html_text(content)


def clean_text(text):
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text):
    text = clean_text(text)
    if not text:
        return []

    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > MAX_CHUNK_CHARS:
            if current:
                chunks.append(current.strip())
                current = ""
            for start in range(0, len(paragraph), MAX_CHUNK_CHARS - CHUNK_OVERLAP_CHARS):
                chunk = paragraph[start : start + MAX_CHUNK_CHARS].strip()
                if chunk:
                    chunks.append(chunk)
            continue

        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= MAX_CHUNK_CHARS:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            current = paragraph

    if current:
        chunks.append(current.strip())

    merged_chunks = []
    for chunk in chunks:
        if merged_chunks and len(chunk) < MIN_CHUNK_CHARS:
            candidate = f"{merged_chunks[-1]}\n\n{chunk}".strip()
            if len(candidate) <= MAX_CHUNK_CHARS:
                merged_chunks[-1] = candidate
                continue
        merged_chunks.append(chunk)

    return merged_chunks


def chunk_id(source_id, chunk_index):
    return f"{source_id}-CHUNK-{chunk_index:04d}"


def metadata_from_row(row):
    return {
        "source_id": row["source_id"],
        "url": row["url"],
        "title": row.get("title", ""),
        "source_type": row.get("source_type", ""),
        "scheme_name": row.get("scheme_name", ""),
        "topic": row.get("topic", ""),
    }


def write_chunks(chunks):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with CHUNKS_PATH.open("w", encoding="utf-8") as chunks_file:
        for chunk in chunks:
            chunks_file.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def store_chunks_in_vector_store(chunks):
    if not chunks:
        return 0

    documents = [chunk["text"] for chunk in chunks]
    embeddings = embed_texts(documents)
    embedded_chunks = [
        {
            **chunk,
            "embedding": embeddings[index],
        }
        for index, chunk in enumerate(chunks)
    ]
    return get_vector_store().add_chunks(embedded_chunks)


def ingest_sources():
    load_dotenv(PROJECT_ROOT / ".env")
    rows = load_manifest()
    all_chunks = []
    failures = []

    for row in rows:
        source_id = row["source_id"]
        url = row["url"]
        try:
            content, content_type = fetch_url(url)
            text = extract_text(url, content, content_type)
            chunks = chunk_text(text)
            for index, chunk in enumerate(chunks, start=1):
                all_chunks.append(
                    {
                        "id": chunk_id(source_id, index),
                        "text": chunk,
                        "metadata": metadata_from_row(row),
                    }
                )
            print(f"{source_id}: extracted {len(chunks)} chunks")
        except Exception as error:
            failures.append({"source_id": source_id, "url": url, "error": str(error)})
            print(f"{source_id}: failed - {error}")

    write_chunks(all_chunks)
    stored_count = store_chunks_in_vector_store(all_chunks)
    print(f"Wrote {len(all_chunks)} chunks to {CHUNKS_PATH}")
    print(f"Stored {stored_count} chunks using VECTOR_BACKEND={vector_backend()}")
    print(f"Embedding model: {EMBEDDING_MODEL}")

    if failures:
        failure_path = PROCESSED_DIR / "ingest_failures.json"
        failure_path.write_text(json.dumps(failures, indent=2), encoding="utf-8")
        print(f"Recorded {len(failures)} failures at {failure_path}")


if __name__ == "__main__":
    ingest_sources()
