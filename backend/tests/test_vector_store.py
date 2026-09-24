import tempfile
import pytest
from backend.app.db.vector_store import EmbeddedVectorStore, VectorDocument


@pytest.mark.asyncio
async def test_vector_store_operations():
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = EmbeddedVectorStore(storage_dir=tmp_dir)

        # 1. Initially empty
        assert await store.count() == 0

        # 2. Add sample embeddings
        doc_a = VectorDocument(
            id="doc-1",
            text="Quantum physics and mechanics",
            vector=[1.0, 0.0, 0.0],
            metadata={"category": "science"},
        )
        doc_b = VectorDocument(
            id="doc-2",
            text="Cooking Italian pasta",
            vector=[0.0, 1.0, 0.0],
            metadata={"category": "culinary"},
        )
        doc_c = VectorDocument(
            id="doc-3",
            text="Quantum computing fundamentals",
            vector=[0.9, 0.1, 0.0],
            metadata={"category": "science"},
        )

        doc_ids = await store.add_documents([doc_a, doc_b, doc_c])
        assert len(doc_ids) == 3
        assert await store.count() == 3

        # 3. Similarity search for query close to Quantum physics
        query = [0.95, 0.05, 0.0]
        results = await store.similarity_search(query_vector=query, top_k=2)

        assert len(results) == 2
        # Doc A or C should be top matches
        assert results[0].document.id in ["doc-1", "doc-3"]
        assert results[0].score > 0.8

        # 4. Filter by metadata
        filtered_results = await store.similarity_search(
            query_vector=query,
            top_k=5,
            filter_meta={"category": "culinary"},
        )
        assert len(filtered_results) == 1
        assert filtered_results[0].document.id == "doc-2"

        # 5. Delete document
        await store.delete(["doc-2"])
        assert await store.count() == 2

        # 6. Verify persistence across reloads
        store_reloaded = EmbeddedVectorStore(storage_dir=tmp_dir)
        assert await store_reloaded.count() == 2

        # 7. Health check
        health = await store.health_check()
        assert health["status"] == "ready"
        assert health["vector_count"] == 2
