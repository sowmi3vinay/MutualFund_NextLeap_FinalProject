import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TABLE_NAME = "document_chunks"


def _load_environment():
    load_dotenv(PROJECT_ROOT / ".env")


class SupabaseVectorStore:
    def __init__(self):
        _load_environment()
        supabase_url = os.getenv("SUPABASE_URL")
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not service_role_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required when VECTOR_BACKEND=supabase."
            )
        self.client = create_client(supabase_url, service_role_key)
        self.table_name = os.getenv("SUPABASE_VECTOR_TABLE", DEFAULT_TABLE_NAME)

    def add_chunks(self, chunks):
        if not chunks:
            return 0

        rows = []
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            rows.append(
                {
                    "id": chunk["id"],
                    "source_id": metadata.get("source_id", ""),
                    "url": metadata.get("url", ""),
                    "title": metadata.get("title", ""),
                    "source_type": metadata.get("source_type", ""),
                    "scheme_name": metadata.get("scheme_name", ""),
                    "topic": metadata.get("topic", ""),
                    "chunk_text": chunk.get("text", ""),
                    "embedding": chunk["embedding"],
                }
            )

        batch_size = 100
        upserted_count = 0
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            self.client.table(self.table_name).upsert(batch, on_conflict="id").execute()
            upserted_count += len(batch)
        return upserted_count

    def search(self, query_embedding, top_k=5):
        response = self.client.rpc(
            "match_document_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": top_k,
            },
        ).execute()
        rows = response.data or []
        chunks = []
        for row in rows:
            similarity = row.get("similarity")
            distance = None if similarity is None else 1 - float(similarity)
            text = row.get("chunk_text", "")
            chunks.append(
                {
                    "id": row.get("id"),
                    "text": text,
                    "chunk_text": text,
                    "distance": distance,
                    "similarity": similarity,
                    "source_id": row.get("source_id"),
                    "url": row.get("url"),
                    "title": row.get("title"),
                    "source_type": row.get("source_type"),
                    "scheme_name": row.get("scheme_name"),
                    "topic": row.get("topic"),
                }
            )
        return chunks

    def count(self):
        response = (
            self.client.table(self.table_name)
            .select("id", count="exact")
            .limit(1)
            .execute()
        )
        return response.count or 0
