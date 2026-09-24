import json
import logging
import math
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)


class VectorDocument(BaseModel):
    """
    Representation of an item stored in the vector database.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str = Field(description="Original document text or content")
    vector: List[float] = Field(description="Dense vector embedding")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary searchable metadata")


class SearchResult(BaseModel):
    """
    Result returned from a vector similarity search.
    """
    document: VectorDocument
    score: float = Field(description="Cosine similarity score (between -1.0 and 1.0)")


class BaseVectorStore(ABC):
    """
    Abstract Base Class for Vector Database providers.
    Decouples storage backend (Embedded, ChromaDB, Qdrant, pgvector) from JARVIS business logic.
    """

    @abstractmethod
    async def add_documents(self, documents: List[VectorDocument]) -> List[str]:
        """Store documents and their vector embeddings."""
        pass

    @abstractmethod
    async def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_meta: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Retrieve the top-k most similar documents based on cosine distance."""
        pass

    @abstractmethod
    async def delete(self, doc_ids: List[str]) -> None:
        """Delete documents by their IDs."""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Return the total number of stored vectors."""
        pass

    @abstractmethod
    async def persist(self) -> None:
        """Flush changes to disk storage."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Probe vector database status."""
        pass


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


class EmbeddedVectorStore(BaseVectorStore):
    """
    Production-grade open-source embedded vector database.
    Stores dense embeddings locally with cosine similarity indexing and atomic disk persistence.
    Zero external dependencies, ideal for local-first operations and fast testing.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or get_settings().VECTOR_STORE_PATH)
        self.index_file = self.storage_dir / "vector_index.json"
        self._documents: Dict[str, VectorDocument] = {}
        self._load()

    def _load(self) -> None:
        """Loads persisted documents from disk if index exists."""
        if not self.index_file.exists():
            return
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                for item in raw_data:
                    doc = VectorDocument(**item)
                    self._documents[doc.id] = doc
            logger.info(f"Loaded {len(self._documents)} documents from vector store at {self.index_file}")
        except Exception as exc:
            logger.error(f"Failed to load vector store from {self.index_file}: {exc}")

    async def persist(self) -> None:
        """Flushes in-memory document index to disk atomically."""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            temp_file = self.storage_dir / "vector_index.tmp"
            data = [doc.model_dump() for doc in self._documents.values()]
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_file, self.index_file)
            logger.debug(f"Persisted {len(self._documents)} vectors to {self.index_file}")
        except Exception as exc:
            logger.error(f"Failed to persist vector index to {self.index_file}: {exc}")

    async def add_documents(self, documents: List[VectorDocument]) -> List[str]:
        doc_ids = []
        for doc in documents:
            self._documents[doc.id] = doc
            doc_ids.append(doc.id)
        await self.persist()
        return doc_ids

    async def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_meta: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        results: List[SearchResult] = []

        for doc in self._documents.values():
            # Apply metadata filters if provided
            if filter_meta:
                match = all(doc.metadata.get(k) == v for k, v in filter_meta.items())
                if not match:
                    continue

            score = _cosine_similarity(query_vector, doc.vector)
            results.append(SearchResult(document=doc, score=score))

        # Sort descending by cosine similarity score
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    async def delete(self, doc_ids: List[str]) -> None:
        for doc_id in doc_ids:
            self._documents.pop(doc_id, None)
        await self.persist()

    async def count(self) -> int:
        return len(self._documents)

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ready",
            "type": "embedded_vector_store",
            "path": str(self.storage_dir),
            "vector_count": len(self._documents),
            "persistence": "enabled",
        }


# Singleton instance
_vector_store_instance: Optional[BaseVectorStore] = None


def get_vector_store() -> BaseVectorStore:
    """Return the global vector store instance."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = EmbeddedVectorStore()
    return _vector_store_instance
