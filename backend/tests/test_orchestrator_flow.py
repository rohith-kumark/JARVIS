import pytest
from backend.app.llm.base import BaseLLMClient, ChatMessage, LLMResponse, ToolCall
from backend.app.llm.mock import MockLLMClient
from backend.app.services.orchestrator import AgentOrchestrator
from backend.app.tools.base import BaseTool, PermissionLevel
from backend.app.tools.registry import ToolRegistry


class ScriptedLLMClient(BaseLLMClient):
    """A mock LLM client that returns scripted responses to test specific orchestrator paths."""
    def __init__(self, responses):
        self._responses = list(responses)
        self._call_count = 0
        self.received_messages = []

    @property
    def provider_name(self) -> str:
        return "scripted-test"

    async def generate(self, messages, tools=None, system_instruction=None, **kwargs):
        self.received_messages.append(list(messages))
        if self._call_count < len(self._responses):
            resp = self._responses[self._call_count]
            self._call_count += 1
            return resp
        return LLMResponse(content="Default fallback completion", model="test")

    async def generate_stream(self, messages, tools=None, **kwargs):
        resp = await self.generate(messages, tools, **kwargs)
        yield resp.content or ""


@pytest.mark.asyncio
async def test_orchestrator_direct_answer_flow():
    """Verify orchestrator returns immediately when LLM answers directly without tools."""
    llm = ScriptedLLMClient([
        LLMResponse(content="Good evening commander. All systems operational.", model="test")
    ])
    orchestrator = AgentOrchestrator(llm_client=llm)

    response = await orchestrator.run_loop(user_message="Hello JARVIS")

    assert response.reply == "Good evening commander. All systems operational."
    assert len(response.tool_executions) == 0
    assert response.llm_provider == "scripted-test"


@pytest.mark.asyncio
async def test_orchestrator_single_tool_call_flow():
    """Verify orchestrator executes a single tool call and feeds result back to LLM."""
    test_registry = ToolRegistry()
    test_registry.discover_builtin_tools()

    llm = ScriptedLLMClient([
        # Turn 1: Model requests calculator tool
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCall(id="call_1", name="calculator", arguments={"expression": "100 / 4"})
            ],
            model="test"
        ),
        # Turn 2: Model synthesizes answer from tool result
        LLMResponse(
            content="100 divided by 4 is exactly 25.",
            model="test"
        )
    ])

    orchestrator = AgentOrchestrator(llm_client=llm, tool_registry=test_registry)
    response = await orchestrator.run_loop(user_message="What is 100 divided by 4?")

    assert response.reply == "100 divided by 4 is exactly 25."
    assert len(response.tool_executions) == 1
    assert response.tool_executions[0].tool_name == "calculator"
    assert response.tool_executions[0].success is True
    assert response.tool_executions[0].data["result"] == 25


@pytest.mark.asyncio
async def test_orchestrator_multiple_tools_flow():
    """Verify orchestrator executes multiple tool calls requested in a single turn."""
    test_registry = ToolRegistry()
    test_registry.discover_builtin_tools()

    llm = ScriptedLLMClient([
        # Turn 1: Model requests both get_current_time and calculator
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCall(id="call_t", name="get_current_time", arguments={"timezone": "UTC"}),
                ToolCall(id="call_c", name="calculator", arguments={"expression": "15 * 15"}),
            ],
            model="test"
        ),
        # Turn 2: Final synthesized answer
        LLMResponse(
            content="The current UTC time has been retrieved, and 15 * 15 is 225.",
            model="test"
        )
    ])

    events_captured = []
    async def capture_event(ev_name, data):
        events_captured.append((ev_name, data))

    orchestrator = AgentOrchestrator(llm_client=llm, tool_registry=test_registry)
    response = await orchestrator.run_loop(
        user_message="Tell me the time and calculate 15 * 15",
        event_callback=capture_event,
    )

    assert response.reply == "The current UTC time has been retrieved, and 15 * 15 is 225."
    assert len(response.tool_executions) == 2
    tool_names = [t.tool_name for t in response.tool_executions]
    assert "get_current_time" in tool_names
    assert "calculator" in tool_names

    # Verify telemetry events streamed
    event_names = [e[0] for e in events_captured]
    assert "tool_start" in event_names
    assert "tool_complete" in event_names


@pytest.mark.asyncio
async def test_orchestrator_unknown_tool_rejection():
    """Verify orchestrator handles unknown tool requests from LLM safely."""
    test_registry = ToolRegistry()

    llm = ScriptedLLMClient([
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCall(id="call_bad", name="malicious_unregistered_tool", arguments={})
            ],
            model="test"
        ),
        LLMResponse(
            content="I was unable to perform that action because the requested tool is not permitted.",
            model="test"
        )
    ])

    orchestrator = AgentOrchestrator(llm_client=llm, tool_registry=test_registry)
    response = await orchestrator.run_loop(user_message="Do something forbidden")

    assert len(response.tool_executions) == 1
    assert response.tool_executions[0].success is False
    assert "Unknown tool" in response.tool_executions[0].error
    assert "not permitted" in response.reply
