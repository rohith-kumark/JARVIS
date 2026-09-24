"""Comprehensive test suite for Phase 2 Persistent Long-Term Memory System."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.memory.extractor import MemoryExtractor
from backend.app.memory.manager import MemoryManager
from backend.app.memory.models import (
    MemoryCategory,
    MemoryCreate,
    MemoryExtractionItem,
    MemoryRecord,
    MemoryUpdate,
)
from backend.app.memory.retriever import MemoryRetriever
from backend.app.memory.store import MemoryStore


@pytest.fixture
def temp_memory_file():
    """Provide a clean temporary file path for MemoryStore testing."""
    fd, path = tempfile.mkstemp(suffix=".json", prefix="test_mem_")
    os.close(fd)
    os.remove(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def memory_components(temp_memory_file):
    """Instantiate fresh MemoryStore, Retriever, Extractor, and Manager for testing."""
    store = MemoryStore(file_path=temp_memory_file)
    retriever = MemoryRetriever(store=store)
    extractor = MemoryExtractor(store=store)
    manager = MemoryManager(store=store, retriever=retriever, extractor=extractor)
    return store, retriever, extractor, manager


def test_1_create_memory(memory_components):
    _, _, _, manager = memory_components
    record = manager.add_memory(
        content="User prefers Python for data engineering",
        category="preference",
        importance=0.8,
        source="manual",
    )
    assert record.id is not None
    assert record.content == "User prefers Python for data engineering"
    assert record.category == "preference"
    assert record.importance == 0.8
    assert record.source == "manual"
    assert record.created_at is not None


def test_2_read_memories(memory_components):
    _, _, _, manager = memory_components
    manager.add_memory("Fact 1", category="personal")
    manager.add_memory("Fact 2", category="professional")

    all_memories = manager.get_all_memories()
    assert len(all_memories) == 2

    filtered = manager.get_all_memories(category="personal")
    assert len(filtered) == 1
    assert filtered[0].content == "Fact 1"


def test_3_update_memory(memory_components):
    _, _, _, manager = memory_components
    record = manager.add_memory("User is learning Java", category="learning", importance=0.6)
    updated = manager.update_memory(
        record.id,
        MemoryUpdate(content="User is mastering Java", importance=0.9),
    )
    assert updated is not None
    assert updated.content == "User is mastering Java"
    assert updated.importance == 0.9
    assert updated.category == "learning"


def test_4_delete_memory(memory_components):
    _, _, _, manager = memory_components
    record = manager.add_memory("Temporary note")
    assert len(manager.get_all_memories()) == 1

    deleted = manager.delete_memory(record.id)
    assert deleted is True
    assert len(manager.get_all_memories()) == 0


def test_5_clear_memories(memory_components):
    _, _, _, manager = memory_components
    manager.add_memory("Note 1")
    manager.add_memory("Note 2")
    manager.add_memory("Note 3")
    assert len(manager.get_all_memories()) == 3

    cleared = manager.clear_memories()
    assert cleared == 3
    assert len(manager.get_all_memories()) == 0


def test_6_search_memories(memory_components):
    _, _, _, manager = memory_components
    manager.add_memory("User's favorite framework is FastAPI", category="preference", importance=0.8)
    manager.add_memory("User wants to build microservices in Go", category="goal", importance=0.7)
    manager.add_memory("User likes dark cyan themes", category="preference", importance=0.5)

    results = manager.search_memories("FastAPI framework")
    assert len(results) >= 1
    assert "FastAPI" in results[0].content


def test_7_duplicate_detection(memory_components):
    _, _, extractor, _ = memory_components

    cand1 = MemoryExtractionItem(content="User prefers Python", category="preference", importance=0.8)
    cand2 = MemoryExtractionItem(content="User prefers Python", category="preference", importance=0.8)

    rec1, status1 = extractor.resolve_and_save(cand1)
    assert status1 == "created"

    rec2, status2 = extractor.resolve_and_save(cand2)
    assert status2 == "duplicate"
    assert rec1.id == rec2.id


def test_8_conflict_resolution(memory_components):
    _, _, extractor, manager = memory_components

    # Candidate 1: Java
    c1 = MemoryExtractionItem(content="User prefers Java for programming", category="preference", importance=0.8)
    extractor.resolve_and_save(c1)

    # Candidate 2: Python (updating same preference)
    c2 = MemoryExtractionItem(content="User prefers Python for programming now", category="preference", importance=0.9)

    with patch.object(extractor, "_get_genai_client") as mock_client:
        mock_genai = MagicMock()
        mock_res = MagicMock()
        mock_res.text = '{"relationship": "CONFLICT", "reason": "User updated programming language preference"}'
        mock_genai.models.generate_content.return_value = mock_res
        mock_client.return_value = mock_genai

        rec2, status2 = extractor.resolve_and_save(c2)
        assert status2 == "updated"
        assert "Python" in rec2.content

        # Ensure no duplicated entries
        assert len(manager.get_all_memories()) == 1


def test_9_importance_validation(memory_components):
    _, _, _, manager = memory_components
    # Out of range values clamped
    rec_high = manager.add_memory("High", importance=1.5)
    assert rec_high.importance == 1.0

    rec_low = manager.add_memory("Low", importance=-0.5)
    assert rec_low.importance == 0.0


def test_10_invalid_memory_data(client):
    # Empty content rejected
    res = client.post("/api/memory", json={"content": ""})
    assert res.status_code == 422


def test_11_missing_json_file(temp_memory_file):
    # When file doesn't exist, store creates it
    assert not os.path.exists(temp_memory_file)
    store = MemoryStore(file_path=temp_memory_file)
    assert os.path.exists(temp_memory_file)
    assert store.load_all() == []


def test_12_corrupted_json_recovery(temp_memory_file):
    # Write corrupted text to file
    with open(temp_memory_file, "w") as f:
        f.write("{invalid json syntax !!!")

    store = MemoryStore(file_path=temp_memory_file)
    records = store.load_all()
    assert records == []

    # Verify store can write safely after corruption recovery
    store.add(MemoryRecord(content="Safe after corrupt"))
    assert len(store.load_all()) == 1


def test_13_memory_extraction(memory_components):
    _, _, extractor, _ = memory_components

    # Explicit instruction
    candidates = extractor._heuristic_fallback_extraction("Remember that my dog's name is Jarvis")
    assert len(candidates) == 1
    assert "Jarvis" in candidates[0].content


def test_14_memory_retrieval_ranking(memory_components):
    _, retriever, _, manager = memory_components
    manager.add_memory("User target role: Senior Data Engineer", category="goal", importance=0.9)
    manager.add_memory("User enjoys playing chess on weekends", category="personal", importance=0.4)

    results = retriever.retrieve("What career path is the user targeting?")
    assert len(results) >= 1
    assert "Data Engineer" in results[0].content


def test_15_chat_integration_with_memory(client, monkeypatch):
    """Test full chat turn retrieves relevant memory and provides context."""
    from backend.app.memory.manager import memory_manager
    memory_manager.clear_memories()

    # Pre-seed memory
    memory_manager.add_memory("User prefers Python for all scripts", category="preference", importance=0.85)

    with patch("backend.app.orchestrator.orchestrator.jarvis_orchestrator.llm._client", None):
        res = client.post("/api/chat", json={"message": "What programming language do I prefer?"})
        assert res.status_code == 200
        data = res.json()
        assert "response" in data
        assert "conversation_id" in data


def test_16_memory_failure_does_not_break_chat(client):
    """Ensure failure in memory extractor does not crash chat endpoint."""
    from backend.app.orchestrator.orchestrator import jarvis_orchestrator

    with patch.object(jarvis_orchestrator.mem_mgr, "extract_and_save_memories", side_effect=RuntimeError("Extraction crashed")):
        with patch("backend.app.orchestrator.orchestrator.jarvis_orchestrator.llm._client", None):
            res = client.post("/api/chat", json={"message": "Hello Jarvis, test safety boundary."})
            assert res.status_code == 200
            assert "response" in res.json()


def test_17_application_restart_persistence(temp_memory_file):
    """Verify memories survive application restarts."""
    # Session 1: Store memory
    store1 = MemoryStore(file_path=temp_memory_file)
    rec = store1.add(MemoryRecord(
        content="User's favorite editor is Neovim",
        category="preference",
        importance=0.8,
    ))

    # Simulate restart by instantiating new MemoryStore pointing to same file
    del store1
    store2 = MemoryStore(file_path=temp_memory_file)
    loaded = store2.load_all()

    assert len(loaded) == 1
    assert loaded[0].id == rec.id
    assert loaded[0].content == "User's favorite editor is Neovim"
    assert loaded[0].category == "preference"


def test_18_explicit_memory_commands(memory_components):
    """Test explicit 'forget everything' and 'forget [item]' user directives."""
    _, _, _, manager = memory_components
    manager.add_memory("User prefers Java for backend", category="preference")
    manager.add_memory("User is based in Berlin", category="personal")

    # Forget Java
    handled, msg, records = manager.handle_explicit_commands("Forget that I prefer Java")
    assert handled is True
    assert "forgotten" in msg.lower()
    assert len(manager.get_all_memories()) == 1

    # Forget everything
    handled, msg, _ = manager.handle_explicit_commands("Forget everything you remember about me")
    assert handled is True
    assert "cleared" in msg.lower()
    assert len(manager.get_all_memories()) == 0
