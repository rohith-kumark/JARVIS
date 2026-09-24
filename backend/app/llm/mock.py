import asyncio
import json
import logging
import re
from typing import Any, AsyncIterator, Dict, List, Optional
from backend.app.llm.base import BaseLLMClient, ChatMessage, LLMResponse, MessageRole, ToolCall

logger = logging.getLogger(__name__)


class MockLLMClient(BaseLLMClient):
    """
    Simulated LLM client for testing and offline development.
    Demonstrates:
    - Direct textual answers without tools
    - Single tool call requests
    - Multiple tool call requests in a single turn
    - Multi-turn tool feedback synthesis
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
        """Simulate LLM reasoning, decision-making, and tool dispatch."""
        await asyncio.sleep(0.01)

        if not messages:
            return LLMResponse(content="Greetings. I am JARVIS. How may I assist you today?", model=self._model)

        last_message = messages[-1]

        # 1. Synthesis turn: If preceding turn was one or more tool executions
        if last_message.role == MessageRole.TOOL:
            # Collect all tool results from the recent exchange
            tool_outputs = []
            for msg in reversed(messages):
                if msg.role == MessageRole.TOOL:
                    try:
                        parsed = json.loads(msg.content or "{}")
                        tool_outputs.append((msg.name, parsed.get("data") or parsed))
                    except Exception:
                        tool_outputs.append((msg.name, msg.content))
                else:
                    break

            summary_parts = []
            for name, output in reversed(tool_outputs):
                if name == "get_current_time" and isinstance(output, dict):
                    summary_parts.append(f"Current time is {output.get('formatted', output.get('iso_8601'))}")
                elif name == "calculator" and isinstance(output, dict):
                    summary_parts.append(f"Calculation `{output.get('expression')}` evaluated to {output.get('result')}")
                elif name in ("system_info", "get_system_info") and isinstance(output, dict):
                    summary_parts.append(f"System status is {output.get('status')} on {output.get('os_name')} ({output.get('machine')})")
                else:
                    summary_parts.append(f"Tool `{name}` completed successfully with result: {output}")

            final_text = "Analysis complete. " + ". ".join(summary_parts) + "."
            return LLMResponse(content=final_text, model=self._model)

        # 2. Decision turn: Evaluate user directive
        user_query = (last_message.content or "").strip()
        query_lower = user_query.lower()

        # Multi-tool scenario check: requests both time and calculation
        has_time_intent = any(k in query_lower for k in ["time", "clock", "date", "timezone"])
        has_math_intent = any(k in query_lower for k in ["calculate", "calc", "math", "+", "-", "*", "/", "sqrt"])
        has_sys_intent = any(k in query_lower for k in ["system", "status", "diagnostics", "platform", "cores"])

        # Multiple tools in a single turn:
        if has_time_intent and has_math_intent:
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_time_001",
                        name="get_current_time",
                        arguments={"timezone": "UTC"}
                    ),
                    ToolCall(
                        id="call_calc_001",
                        name="calculator",
                        arguments={"expression": "12 * 12"}
                    )
                ],
                model=self._model,
            )

        # Single tool: Calculator
        if has_math_intent:
            # Extract expression or default to 2 + 2
            expr_match = re.search(r'(?:calculate|compute|calc|what is)\s+([0-9\+\-\*\/\(\)\.\s\^%sqrtcossin]+)', user_query, re.IGNORECASE)
            expression = expr_match.group(1).strip() if expr_match else "42 * 2"
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_calc_single",
                        name="calculator",
                        arguments={"expression": expression}
                    )
                ],
                model=self._model,
            )

        # Single tool: Current Time
        if has_time_intent:
            tz = "UTC"
            if "tokyo" in query_lower:
                tz = "Asia/Tokyo"
            elif "new york" in query_lower:
                tz = "America/New_York"
            elif "london" in query_lower:
                tz = "Europe/London"
            elif "kolkata" in query_lower or "india" in query_lower:
                tz = "Asia/Kolkata"

            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_time_single",
                        name="get_current_time",
                        arguments={"timezone": tz}
                    )
                ],
                model=self._model,
            )

        # Single tool: System Info
        if has_sys_intent:
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_sysinfo_single",
                        name="system_info",
                        arguments={"include_environment": True}
                    )
                ],
                model=self._model,
            )

        # Direct response without tool calls
        return LLMResponse(
            content=f"JARVIS Core online. Directive received: '{user_query}'. All cognitive subsystems operational.",
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
        """Stream simulated response."""
        response = await self.generate(messages, tools, system_instruction, temperature, **kwargs)
        text = response.content or "Processing complete."
        for word in text.split(" "):
            await asyncio.sleep(0.01)
            yield word + " "
