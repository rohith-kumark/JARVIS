import json
import pytest
from starlette.testclient import TestClient
from backend.app.main import app


def test_websocket_lifecycle():
    client = TestClient(app)
    with client.websocket_connect("/api/ws") as websocket:
        # 1. Expect connection_ack
        ack_data = websocket.receive_json()
        assert ack_data["type"] == "connection_ack"
        assert ack_data["payload"]["status"] == "connected"

        # 2. Test Ping / Pong
        websocket.send_json({"type": "ping", "payload": {}})
        pong_data = websocket.receive_json()
        assert pong_data["type"] == "pong"

        # 3. Test User Message
        websocket.send_json({
            "type": "user_message",
            "payload": {
                "content": "Check system status",
                "caller_permission": "admin"
            }
        })

        # Receive streamed events (thinking, tool_start, tool_complete, agent_message)
        received_types = []
        for _ in range(5):
            msg = websocket.receive_json()
            received_types.append(msg["type"])
            if msg["type"] == "agent_message":
                assert "reply" in msg["payload"]
                break

        assert "agent_message" in received_types
