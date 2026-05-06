import os
import threading

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct


load_dotenv()

qdrant_lock = threading.RLock()


class QdrantStorage:
    def __init__(self, url=None, collection=None, dim=None):
        qdrant_url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        vector_dim = int(dim or os.getenv("QDRANT_DIM", os.getenv("EMBED_DIM", "3072")))
        self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=30)
        self.collection = collection or os.getenv("QDRANT_COLLECTION", "docs")
        with qdrant_lock:
            if not self.client.collection_exists(self.collection):
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
                )

            
    def upsert(self, ids, vectors, payloads):
        points = [PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i]) for i in range(len(ids))]
        with qdrant_lock:
            self.client.upsert(self.collection, points=points)


    def search(self, query_vector, top_k: int = 5):
        with qdrant_lock:
            response = self.client.query_points(
                collection_name=self.collection,
                query=query_vector,
                with_payload=True,
                limit=top_k,
            )
        results = getattr(response, "points", response)
        contexts = []
        sources = set()

        for r in results:
            payload = getattr(r, "payload", None) or {}
            text = payload.get("text", "")
            source = payload.get("source", "")
            if text:
                contexts.append(text)
                sources.add(source)

        return {"contexts": contexts, "sources": list(sources)}
