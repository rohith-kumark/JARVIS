import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional
from backend.app.llm.base import BaseLLMClient, ChatMessage, LLMResponse, MessageRole, ToolCall

logger = logging.getLogger(__name__)


class MockLLMClient(BaseLLMClient):
    """
    Simulated LLM client for offline development, integration tests,
    and running JARVIS before a Gemini API key is configured.
    """

    def __init__(self, model: str = "mock-reasoning-engine"):
        self._model = model

    @property
    def provider_name(self) -> str:
        return "mock"

    async def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Simulate LLM reasoning and controlled tool dispatch."""
        await asyncio.sleep(0.05)  # Simulate network latency

        if not messages:
            return LLMResponse(content="Greetings. I am JARVIS. How may I assist you today?", model=self._model)

        last_message = messages[-1]

        # 1. If previous turn was a tool execution result, synthesize answer
        if last_message.role == MessageRole.TOOL:
            tool_name = last_message.name or "tool"
            return LLMResponse(
                content=(
                    f"I have successfully executed the `{tool_name}` tool. "
                    f"Telemetry output: {last_message.content}. All systems are operating within normal parameters."
                ),
                model=self._model,
            )

        # 2. If user message requests system status or diagnostics, trigger the get_system_info tool
        query = (last_message.content or "").lower()
        if any(keyword in query for keyword in ["system", "status", "time", "health", "diagnostics", "info"]):
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_sysinfo_001",
                        name="get_system_info",
                        arguments={"include_environment": True}
                    )
                ],
                model=self._model,
            )

        # 3. Default assistant conversational reply
        return LLMResponse(
            content=f"JARVIS Core online. Received directive: '{last_message.content}'. Standing by for your instructions.",
            model=self._model,
        )

    async def generate_stream(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream simulated tokens."""
        response = await self.generate(messages, tools, system_instruction, temperature, **kwargs)
        text = response.content or "Processing complete."
        words = text.split(" ")
        for word in words:
            await asyncio.sleep(0.02)
            yield word + " "
