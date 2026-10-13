import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add paths
backend_dir = str(Path(__file__).resolve().parent.parent)
agentify_dir = str(Path(__file__).resolve().parent.parent / "agentify")
for p in [backend_dir, agentify_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import (
    ASTRA_DB_API_TOKEN,
    ASTRA_DB_ENDPOINT,
    ASTRA_DB_KEYSPACE,
    COLLECTION_NAME,
    GEMINI_API_KEY,
    GEMINI_MODEL
)
from vector_db import VectorDB
from agents import BaseAgent
from file_processor import FileProcessor

logger = logging.getLogger("ragchat.embedder")


class VectorEmbedder:
    """Embeds processed document chunks into Astra DB and the local vector store."""
    def __init__(
        self,
        vector_db: Optional[VectorDB] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.vector_db = vector_db or VectorDB()
        self.api_key = api_key or GEMINI_API_KEY
        self.model_name = model_name or GEMINI_MODEL
        self.agent = BaseAgent(api_key=self.api_key, model_name=self.model_name)
        self.processor = FileProcessor()

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Gemini or deterministic vector fallback."""
        return self.agent.generate_embedding(text)

    def embed_chunk(self, chunk: Dict[str, Any]) -> bool:
        """Embed an individual chunk dictionary."""
        filename = chunk.get("filename", "unknown")
        content = chunk.get("content", "")
        metadata = chunk.get("metadata", {})
        metadata["chunk_index"] = chunk.get("chunk_index", 0)
        metadata["total_chunks"] = chunk.get("total_chunks", 1)

        vector = self.generate_embedding(content)
        return self.vector_db.insert(
            filename=filename,
            content=content,
            vector=vector,
            metadata=metadata
        )

    def embed_file(self, file_path: str) -> int:
        """Process a file and embed all its chunks into the vector store."""
        chunks = self.processor.process_file(file_path)
        count = 0
        for chunk in chunks:
            if self.embed_chunk(chunk):
                count += 1
        logger.info(f"Embedded {count} chunk(s) for file: {os.path.basename(file_path)}")
        return count

    def embed_url(self, url: str) -> int:
        """Fetch URL content and embed chunks into the vector store."""
        chunks = self.processor.process_url(url)
        count = 0
        for chunk in chunks:
            if self.embed_chunk(chunk):
                count += 1
        logger.info(f"Embedded {count} chunk(s) from URL: {url}")
        return count

    def embed_content(self, filename: str, content: Any):
        """Legacy compatibility wrapper."""
        if isinstance(content, str):
            vector = self.generate_embedding(content)
            self.vector_db.insert(filename, content, vector, {"legacy": True})
        elif isinstance(content, dict) and "text" in content:
            vector = self.generate_embedding(content["text"])
            self.vector_db.insert(filename, content["text"], vector, {"legacy": True})