from pathlib import Path

import chromadb

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VECTOR_STORE_PATH = PROJECT_ROOT / "data" / "vector_store"
COLLECTION_NAME = "mutual_fund_sources"


class ChromaVectorStore:
    def __init__(self, path=VECTOR_STORE_PATH, collection_name=COLLECTION_NAME):
        self.path = path
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=str(self.path))

    def collection(self):
        return self.client.get_or_create_collection(name=self.collection_name)

    def count(self):
        return self.collection().count()

    def add_chunks(self, chunks):
        if not chunks:
            return 0

        collection_names = [collection.name for collection in self.client.list_collections()]
        if self.collection_name in collection_names:
            self.client.delete_collection(self.collection_name)
        collection = self.client.get_or_create_collection(self.collection_name)

        metadatas = []
        for chunk in chunks:
            metadata = dict(chunk["metadata"])
            metadata["id"] = chunk["id"]
            metadatas.append(metadata)

        collection.add(
            ids=[chunk["id"] for chunk in chunks],
            documents=[chunk["text"] for chunk in chunks],
            embeddings=[chunk["embedding"] for chunk in chunks],
            metadatas=metadatas,
        )
        return collection.count()

    def search(self, query_embedding, top_k=5):
        collection = self.collection()
        if collection.count() == 0:
            return []

        candidate_count = max(top_k, min(max(top_k * 10, 50), collection.count()))
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=candidate_count,
            include=["documents", "metadatas", "distances"],
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        chunks = []
        for index, document in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) else {}
            distance = distances[index] if index < len(distances) else None
            similarity = None if distance is None else 1 - float(distance)
            chunks.append(
                {
                    "id": metadata.get("id"),
                    "text": document,
                    "chunk_text": document,
                    "distance": distance,
                    "similarity": similarity,
                    "source_id": metadata.get("source_id"),
                    "url": metadata.get("url"),
                    "title": metadata.get("title"),
                    "source_type": metadata.get("source_type"),
                    "scheme_name": metadata.get("scheme_name"),
                    "topic": metadata.get("topic"),
                }
            )
        return chunks
