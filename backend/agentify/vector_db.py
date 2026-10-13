import os
import json
import math
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from astrapy import DataAPIClient
    ASTRAPY_AVAILABLE = True
except ImportError:
    ASTRAPY_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from config import (
    ASTRA_DB_API_TOKEN,
    ASTRA_DB_ENDPOINT,
    ASTRA_DB_KEYSPACE,
    COLLECTION_NAME,
    OUTPUT_DIR
)

logger = logging.getLogger("ragchat.vector_db")

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if NUMPY_AVAILABLE:
        a = np.array(v1, dtype=np.float32)
        b = np.array(v2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    else:
        dot = sum(x * y for x, y in zip(v1, v2))
        norm_a = math.sqrt(sum(x * x for x in v1))
        norm_b = math.sqrt(sum(y * y for y in v2))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class VectorDB:
    """
    Dual-mode Vector Database:
    1. Astra DB Vector Search (Primary when configured)
    2. Local In-Memory & File-Backed Vector Store (Seamless fallback)
    """
    def __init__(
        self,
        api_token: Optional[str] = None,
        endpoint: Optional[str] = None,
        keyspace: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        self.api_token = (api_token if api_token is not None else ASTRA_DB_API_TOKEN).strip()
        self.endpoint = (endpoint if endpoint is not None else ASTRA_DB_ENDPOINT).strip()
        self.keyspace = (keyspace if keyspace is not None else ASTRA_DB_KEYSPACE).strip()
        self.collection_name = (collection_name if collection_name is not None else COLLECTION_NAME).strip()

        # Local storage directory and cache file
        self.output_dir = Path(OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.local_cache_file = self.output_dir / "local_vector_db.json"

        # Local in-memory document list: [{id, filename, content, vector, metadata}]
        self.local_store: List[Dict[str, Any]] = []
        self._load_local_store()

        # Astra DB handle
        self.astra_client = None
        self.astra_db = None
        self.astra_collection = None
        self.astra_connected = False
        self.connection_message = ""

        self._init_astra()

    def _init_astra(self):
        """Attempt to connect to Astra DB if credentials are provided."""
        if not self.api_token or not self.endpoint:
            self.astra_connected = False
            self.connection_message = "Astra DB not configured. Using high-performance local vector store."
            return

        if not ASTRAPY_AVAILABLE:
            self.astra_connected = False
            self.connection_message = "astrapy library not available. Using local vector store."
            return

        try:
            self.astra_client = DataAPIClient(self.api_token)
            self.astra_db = self.astra_client.get_database_by_api_endpoint(self.endpoint)
            
            # Verify connection
            try:
                self.astra_collection = self.astra_db.get_collection(
                    self.collection_name,
                    keyspace=self.keyspace
                )
                self.astra_collection.estimated_document_count()
                self.astra_connected = True
                self.connection_message = f"Connected to DataStax Astra DB (collection: {self.collection_name})"
                logger.info(self.connection_message)
            except Exception as e_get:
                # Try creating collection with vector support (astrapy 2.x syntax)
                try:
                    try:
                        self.astra_collection = self.astra_db.create_collection(
                            self.collection_name,
                            keyspace=self.keyspace,
                            definition={"vector": {"dimension": 768, "metric": "cosine"}}
                        )
                    except TypeError:
                        self.astra_collection = self.astra_db.create_collection(
                            self.collection_name,
                            keyspace=self.keyspace,
                            dimension=768,
                            metric="cosine"
                        )
                    self.astra_connected = True
                    self.connection_message = f"Created and connected to DataStax Astra DB (collection: {self.collection_name})"
                    logger.info(self.connection_message)
                except Exception as e_create:
                    self.astra_connected = False
                    self.connection_message = f"Astra DB unreachable ({str(e_create)}). Using high-performance local vector store."
                    logger.info(self.connection_message)
        except Exception as e:
            self.astra_connected = False
            self.connection_message = f"Astra DB connection failed: {str(e)}. Operating in local vector store mode."
            logger.info(self.connection_message)

    def _load_local_store(self):
        """Load local vector store from disk if present."""
        if self.local_cache_file.exists():
            try:
                with open(self.local_cache_file, "r", encoding="utf-8") as f:
                    self.local_store = json.load(f)
            except Exception as e:
                logger.error(f"Error loading local vector store: {e}")
                self.local_store = []

    def _save_local_store(self):
        """Save local vector store to disk."""
        try:
            with open(self.local_cache_file, "w", encoding="utf-8") as f:
                json.dump(self.local_store, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving local vector store: {e}")

    def insert(self, filename: str, content: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Insert a document chunk into vector store (both Astra DB if available and local store)."""
        doc = {
            "id": f"{filename}_{len(self.local_store)}",
            "filename": filename,
            "content": content,
            "vector": vector,
            "metadata": metadata or {}
        }

        # 1. Always store locally for instant resilience & offline support
        self.local_store.append(doc)
        self._save_local_store()

        # 2. Store in Astra DB if connected
        if self.astra_connected and self.astra_collection:
            try:
                astra_doc = {
                    "filename": filename,
                    "content": content,
                    "$vector": vector,
                    "metadata": metadata or {}
                }
                self.astra_collection.insert_one(astra_doc)
            except Exception as e:
                logger.warning(f"Failed to insert into Astra DB: {e}")

        return True

    def insert_many(self, items: List[Dict[str, Any]]) -> int:
        """Insert multiple documents."""
        count = 0
        for item in items:
            filename = item.get("filename", "unknown")
            content = item.get("content", "")
            vector = item.get("vector") or item.get("$vector", [])
            metadata = item.get("metadata", {})
            if self.insert(filename, content, vector, metadata):
                count += 1
        return count

    def query(self, embedding: List[float], top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query vector store for closest documents.
        Uses Astra DB vector search if connected; falls back to local cosine similarity.
        """
        # If Astra DB is connected, try querying it
        if self.astra_connected and self.astra_collection:
            try:
                find_filter = filters or {}
                results = self.astra_collection.find(
                    filter=find_filter,
                    sort={"$vector": embedding},
                    limit=top_k
                )
                output = []
                for doc in results:
                    output.append({
                        "filename": doc.get("filename", "unknown"),
                        "content": doc.get("content", ""),
                        "score": doc.get("$similarity", 1.0),
                        "metadata": doc.get("metadata", {})
                    })
                if output:
                    return output
            except Exception as e:
                logger.warning(f"Astra DB query error: {e}. Falling back to local store.")

        # Local vector store query
        if not self.local_store:
            return []

        scored = []
        for doc in self.local_store:
            doc_vec = doc.get("vector", [])
            if not doc_vec:
                continue

            # Check filters if provided
            if filters:
                meta = doc.get("metadata", {})
                match = all(meta.get(k) == v or doc.get(k) == v for k, v in filters.items())
                if not match:
                    continue

            sim = cosine_similarity(embedding, doc_vec)
            scored.append((sim, doc))

        # Sort descending by similarity
        scored.sort(key=lambda x: x[0], reverse=True)
        top_results = scored[:top_k]

        return [
            {
                "filename": doc.get("filename", "unknown"),
                "content": doc.get("content", ""),
                "score": round(score, 4),
                "metadata": doc.get("metadata", {})
            }
            for score, doc in top_results
        ]

    def list_documents(self) -> List[Dict[str, Any]]:
        """Return list of distinct documents and chunk counts."""
        doc_stats: Dict[str, Dict[str, Any]] = {}
        for item in self.local_store:
            fn = item.get("filename", "unknown")
            if fn not in doc_stats:
                meta = item.get("metadata", {})
                doc_stats[fn] = {
                    "filename": fn,
                    "chunks": 0,
                    "type": meta.get("type", fn.split(".")[-1] if "." in fn else "unknown"),
                    "length": 0
                }
            doc_stats[fn]["chunks"] += 1
            doc_stats[fn]["length"] += len(item.get("content", ""))

        return list(doc_stats.values())

    def clear(self) -> bool:
        """Clear local vector store and Astra collection if possible."""
        self.local_store = []
        self._save_local_store()

        if self.astra_connected and self.astra_collection:
            try:
                self.astra_collection.delete_many({})
            except Exception as e:
                logger.warning(f"Failed to clear Astra DB: {e}")
        return True

    def count(self) -> int:
        """Return total document chunk count."""
        return len(self.local_store)

    def status(self) -> Dict[str, Any]:
        """Return status information about the vector DB."""
        return {
            "astra_connected": self.astra_connected,
            "message": self.connection_message,
            "collection": self.collection_name,
            "endpoint": self.endpoint if self.endpoint else "Not set",
            "document_chunks": len(self.local_store),
            "documents": self.list_documents()
        }