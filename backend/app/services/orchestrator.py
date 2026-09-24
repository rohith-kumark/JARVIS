import json
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional
from backend.app.core.exceptions import ToolException
from backend.app.llm.base import BaseLLMClient, ChatMessage, MessageRole, ToolCall
from backend.app.schemas.chat import ChatResponse, ToolExecutionRecord
from backend.app.tools.base import PermissionLevel
from backend.app.tools.registry import ToolRegistry, registry as default_tool_registry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are JARVIS, an advanced modular AI personal assistant.
Your architecture uses Gemini for reasoning and Python for safe, controlled execution.
You have access to a set of controlled tools. When a user asks you for system information,
diagnostics, time, or tasks requiring an action, invoke the appropriate registered tool.
You can invoke multiple tools in a single turn if needed.
Always verify and explain the results of your tool executions clearly and concisely.
"""


class AgentOrchestrator:
    """
    JARVIS Orchestrator:
    1. Receives a user request.
    2. Sends the request and available tool definitions to Gemini.
    3. Handles Gemini's decision:
       - Direct answer without tools
       - Single tool request
       - Multiple tool requests in parallel
    4. Safely executes requested tools through the Tool Registry:
       - Permission verification
       - Input validation
       - Execution timeouts
       - Structured logging
    5. Returns tool results back to Gemini.
    6. Returns Gemini's final synthesized user-facing response.
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
        Supports direct answers, single tool calls, and multiple tool calls per turn.
        Optional event_callback(event_type: str, data: dict) streams real-time telemetry.
        """
        sid = session_id or str(uuid.uuid4())
        perm = self._parse_permission(caller_permission)
        tool_records: List[ToolExecutionRecord] = []

        # 1. Fetch available function declarations for caller's clearance
        tool_declarations = self._tools.get_function_declarations(max_permission=perm)

        # 2. Build initial conversation turn
        messages: List[ChatMessage] = [
            ChatMessage(role=MessageRole.USER, content=user_message)
        ]

        if event_callback:
            await event_callback("agent_thinking", {"session_id": sid, "message": "Evaluating directive..."})

        iteration = 0
        final_reply = ""

        while iteration < self._max_tool_iterations:
            iteration += 1
            logger.debug(f"[Orchestrator] Loop iteration {iteration} for session {sid}")

            # 3. Query LLM (Gemini or Mock) with conversation history and available tools
            llm_response = await self._llm.generate(
                messages=messages,
                tools=tool_declarations if tool_declarations else None,
                system_instruction=SYSTEM_PROMPT,
            )

            # Case A: Model answered directly without tool calls
            if not llm_response.has_tool_calls:
                final_reply = llm_response.content or "Directive executed."
                break

            # Case B: Model requested one or more tool calls
            logger.info(
                f"[Orchestrator] Model requested {len(llm_response.tool_calls)} tool call(s): "
                f"{[tc.name for tc in llm_response.tool_calls]}"
            )

            # Record model turn with requested tool calls in history
            messages.append(
                ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=llm_response.content,
                    tool_calls=llm_response.tool_calls,
                )
            )

            # 4. Execute all requested tools via the controlled ToolRegistry
            for tool_call in llm_response.tool_calls:
                tool_name = tool_call.name
                tool_args = tool_call.arguments or {}

                logger.info(f"[Orchestrator] Executing tool: '{tool_name}' with arguments: {list(tool_args.keys())}")

                if event_callback:
                    await event_callback(
                        "tool_start",
                        {
                            "tool_name": tool_name,
                            "arguments": tool_args,
                            "session_id": sid,
                        }
                    )

                # Execute controlled tool with permission verification, timeout, and error handling
                result = await self._tools.execute(
                    name=tool_name,
                    arguments=tool_args,
                    caller_permission=perm,
                )

                elapsed_ms = result.metadata.get("execution_time_ms", 0.0)

                record = ToolExecutionRecord(
                    tool_name=tool_name,
                    arguments=tool_args,
                    success=result.success,
                    data=result.data,
                    error=result.error,
                    execution_time_ms=elapsed_ms,
                )
                tool_records.append(record)

                if event_callback:
                    await event_callback(
                        "tool_complete",
                        {
                            "tool_name": tool_name,
                            "success": result.success,
                            "data": result.data,
                            "error": result.error,
                            "execution_time_ms": elapsed_ms,
                            "session_id": sid,
                        }
                    )

                # 5. Append tool execution output to history to return back to Gemini
                serialized_result = json.dumps(result.to_dict())
                messages.append(
                    ChatMessage(
                        role=MessageRole.TOOL,
                        name=tool_name,
                        content=serialized_result,
                        tool_call_id=tool_call.id,
                    )
                )

        # Fallback if loop exceeded max iterations
        if not final_reply:
            if tool_records:
                final_reply = f"Completed execution of {len(tool_records)} tool(s)."
            else:
                final_reply = "Processing completed."

        return ChatResponse(
            reply=final_reply,
            session_id=sid,
            tool_executions=tool_records,
            llm_provider=self._llm.provider_name,
        )
