"""Tests for GET /api/health."""


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "app_name" in data
    assert data["database"] == "connected"
    assert data["tools_count"] >= 2
    assert "calculator" in data["registered_tools"]
    assert "get_current_time" in data["registered_tools"]
