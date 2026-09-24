"""Integration test for Gemini LLM service with real Google GenAI API."""

import pytest
from backend.app.core.config import get_settings
from backend.app.llm.gemini_service import GeminiService
from backend.app.tools.manager import tool_manager
from backend.app.tools.registry import tool_registry

settings = get_settings()


@pytest.mark.skipif(
    not settings.GEMINI_API_KEY,
    reason="GEMINI_API_KEY is not configured",
)
def test_live_gemini_tool_calling():
    """Verify live Gemini API connection and tool execution for calculator."""
    import socket
    try:
        socket.gethostbyname("generativelanguage.googleapis.com")
    except socket.gaierror:
        pytest.skip("Network access to Gemini API is unavailable (sandboxed environment)")

    settings = get_settings()
    tool_registry.register_builtins()
    service = GeminiService(settings=settings, registry=tool_registry, tool_mgr=tool_manager)

    response_text, tool_calls = service.execute_chat_turn(
        user_message="Use the calculator to compute 35 * 14. State the result clearly.",
        conversation_history=[],
    )

    assert len(tool_calls) >= 1
    assert any(c.tool_name == "calculator" for c in tool_calls)
    calc_call = next(c for c in tool_calls if c.tool_name == "calculator")
    assert calc_call.result["result"] == 490
    assert "490" in response_text
