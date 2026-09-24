import json
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional
from backend.app.core.exceptions import ToolException
from backend.app.llm.base import BaseLLMClient, ChatMessage, MessageRole
from backend.app.schemas.chat import ChatResponse, ToolExecutionRecord
from backend.app.tools.base import PermissionLevel
from backend.app.tools.registry import ToolRegistry, registry as default_tool_registry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are JARVIS, an advanced modular AI personal assistant.
Your architecture uses Gemini for reasoning and Python for safe, controlled execution.
You have access to a set of controlled tools. When a user asks you for system information,
diagnostics, time, or tasks requiring an action, invoke the appropriate registered tool.
Always verify and explain the results of your tool executions clearly and concisely.
"""


class AgentOrchestrator:
    """
    Coordinates reasoning and execution:
    1. Evaluates user intent via LLM abstraction.
    2. Dispatches and executes tools through the controlled ToolRegistry.
    3. Feeds tool execution results back to the LLM for synthesis.
    4. Streams real-time telemetry (thinking, tool starts, tool completions).
    """

    def __init__(self, llm_client: BaseLLMClient, tool_registry: Optional[ToolRegistry] = None):
        self._llm = llm_client
        self._tools = tool_registry or default_tool_registry
        self._max_tool_iterations = 5

    @property
    def llm_provider_name(self) -> str:
        return self._llm.provider_name

    def _parse_permission(self, perm_str: str) -> PermissionLevel:
        try:
            return PermissionLevel(perm_str.lower())
        except (ValueError, AttributeError):
            logger.warning(f"Invalid permission '{perm_str}'. Defaulting to READ_ONLY.")
            return PermissionLevel.READ_ONLY

    async def run_loop(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        caller_permission: str = "admin",
        event_callback: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    ) -> ChatResponse:
        """
        Execute the agent reasoning and tool dispatch loop.
        Optional event_callback(event_type: str, data: dict) allows real-time WebSocket telemetry.
        """
        sid = session_id or str(uuid.uuid4())
        perm = self._parse_permission(caller_permission)
        tool_records: List[ToolExecutionRecord] = []

        # Available tool declarations for the caller's clearance
        tool_declarations = self._tools.get_function_declarations(max_permission=perm)

        # Build initial conversation context
        messages: List[ChatMessage] = [
            ChatMessage(role=MessageRole.USER, content=user_message)
        ]

        if event_callback:
            await event_callback("agent_thinking", {"session_id": sid, "message": "Analyzing request..."})

        iteration = 0
        final_reply = ""

        while iteration < self._max_tool_iterations:
            iteration += 1
            logger.debug(f"Reasoning loop iteration {iteration} for session {sid}")

            llm_response = await self._llm.generate(
                messages=messages,
                tools=tool_declarations if tool_declarations else None,
                system_instruction=SYSTEM_PROMPT,
            )

            # If model produced direct textual response without tool calls
            if not llm_response.has_tool_calls:
                final_reply = llm_response.content or "Task completed."
                break

            # Handle tool calls
            for tool_call in llm_response.tool_calls:
                logger.info(f"Agent requested tool call: {tool_call.name} with args {tool_call.arguments}")

                if event_callback:
                    await event_callback(
                        "tool_start",
                        {"tool_name": tool_call.name, "arguments": tool_call.arguments, "session_id": sid}
                    )

                # Execute controlled tool via registry
                result = await self._tools.execute(
                    name=tool_call.name,
                    arguments=tool_call.arguments,
                    caller_permission=perm,
                )

                tool_records.append(
                    ToolExecutionRecord(
                        tool_name=tool_call.name,
                        arguments=tool_call.arguments,
                        success=result.success,
                        data=result.data,
                        error=result.error,
                        execution_time_ms=result.metadata.get("execution_time_ms", 0.0),
                    )
                )

                if event_callback:
                    await event_callback(
                        "tool_complete",
                        {
                            "tool_name": tool_call.name,
                            "success": result.success,
                            "data": result.data,
                            "error": result.error,
                            "session_id": sid,
                        }
                    )

                # Append tool execution result back into conversation history
                serialized_result = json.dumps(result.to_dict())
                messages.append(
                    ChatMessage(
                        role=MessageRole.TOOL,
                        name=tool_call.name,
                        content=serialized_result,
                        tool_call_id=tool_call.id,
                    )
                )

        if not final_reply and tool_records:
            final_reply = f"Executed {len(tool_records)} tool(s) successfully."

        return ChatResponse(
            reply=final_reply,
            session_id=sid,
            tool_executions=tool_records,
            llm_provider=self._llm.provider_name,
        )
