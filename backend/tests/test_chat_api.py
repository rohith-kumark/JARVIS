"""Tests for chat, conversation, and memory API endpoints."""

from unittest.mock import MagicMock, patch
from backend.app.schemas.chat import ToolCallInfo


def test_conversations_crud(client):
    # 1. List initially empty
    res = client.get("/api/conversations")
    assert res.status_code == 200
    assert len(res.json()) == 0

    # 2. Create conversation
    res = client.post("/api/conversations", json={"title": "Custom Session"})
    assert res.status_code == 200
    conv_data = res.json()
    conv_id = conv_data["id"]
    assert conv_data["title"] == "Custom Session"

    # 3. Retrieve conversation detail
    res = client.get(f"/api/conversations/{conv_id}")
    assert res.status_code == 200
    detail = res.json()
    assert detail["id"] == conv_id
    assert len(detail["messages"]) == 0

    # 4. Delete conversation
    res = client.delete(f"/api/conversations/{conv_id}")
    assert res.status_code == 200

    # 5. Verify deleted
    res = client.get(f"/api/conversations/{conv_id}")
    assert res.status_code == 404


def test_memory_endpoint(client):
    res = client.get("/api/memory")
    assert res.status_code == 200
    data = res.json()
    assert "memories" in data
    assert "preferences" in data


def test_chat_validation_error(client):
    # Empty message should be rejected
    res = client.post("/api/chat", json={"message": ""})
    assert res.status_code == 422


def test_chat_endpoint_mock_mode(client):
    """Test /api/chat using mock fallback mode."""
    with patch("backend.app.orchestrator.orchestrator.jarvis_orchestrator.llm._client", None):
        # Time request
        res = client.post("/api/chat", json={"message": "What is the current time?"})
        assert res.status_code == 200
        data = res.json()
        assert "response" in data
        assert data["conversation_id"] is not None
        assert len(data["tool_calls"]) == 1
        assert data["tool_calls"][0]["tool_name"] == "get_current_time"

        conv_id = data["conversation_id"]

        # Calculator request in same conversation
        res2 = client.post("/api/chat", json={"message": "Calculate 25 * 4", "conversation_id": conv_id})
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["conversation_id"] == conv_id
        assert len(data2["tool_calls"]) == 1
        assert data2["tool_calls"][0]["tool_name"] == "calculator"
        assert data2["tool_calls"][0]["result"]["result"] == 100

        # Check conversation history saved
        res3 = client.get(f"/api/conversations/{conv_id}")
        assert res3.status_code == 200
        messages = res3.json()["messages"]
        assert len(messages) == 4  # 2 user + 2 assistant
