import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.llm.mock import MockLLMClient
from backend.app.llm.base import ChatMessage, MessageRole
from backend.app.services.orchestrator import AgentOrchestrator
from backend.app.tools.registry import registry


@pytest.mark.asyncio
async def test_mock_llm_generation():
    client = MockLLMClient()
    messages = [ChatMessage(role=MessageRole.USER, content="Hello JARVIS")]
    response = await client.generate(messages)
    assert response.content is not None
    assert "JARVIS" in response.content


@pytest.mark.asyncio
async def test_orchestrator_tool_calling_loop():
    llm = MockLLMClient()
    orchestrator = AgentOrchestrator(llm_client=llm, tool_registry=registry)

    # Prompt triggering tool call in mock engine
    response = await orchestrator.run_loop(
        user_message="Check system status and diagnostics",
        caller_permission="admin",
    )
    assert len(response.tool_executions) >= 1
    assert response.tool_executions[0].tool_name in ("system_info", "get_system_info")
    assert response.tool_executions[0].success is True
    assert "operational" in response.reply.lower() or "normal" in response.reply.lower()


@pytest.mark.asyncio
async def test_chat_api_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/chat", json={"message": "System diagnostics check"})
        assert res.status_code == 200
        body = res.json()
        assert "reply" in body
        assert "session_id" in body
