"""Gemini LLM Service integrating with Google GenAI SDK."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from google import genai
from google.genai import types

from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import LLMServiceError
from backend.app.schemas.chat import ToolCallInfo
from backend.app.tools.manager import ToolManager, tool_manager
from backend.app.tools.registry import ToolRegistry, tool_registry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are JARVIS (Just A Rather Very Intelligent System), a sophisticated, precise, and helpful personal AI assistant.
Your responses should be concise, articulate, and accurate.
When tools are available and relevant to answer a user's inquiry (such as retrieving the current time or performing mathematical calculations), you MUST call the appropriate tool.
Never fabricate timestamps or perform complex mental calculations without verifying via the calculator tool when available.
"""


class GeminiService:
    """Service wrapper for Google Gemini models using the official google-genai SDK."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        registry: Optional[ToolRegistry] = None,
        tool_mgr: Optional[ToolManager] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.registry = registry or tool_registry
        self.tool_manager = tool_mgr or tool_manager
        self._client: Optional[genai.Client] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Google GenAI client if an API key is available."""
        if self.settings.GEMINI_API_KEY and self.settings.GEMINI_API_KEY.strip():
            try:
                self._client = genai.Client(api_key=self.settings.GEMINI_API_KEY)
                logger.info(
                    f"GeminiService initialized with model '{self.settings.GEMINI_MODEL}'"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")
                self._client = None
        else:
            logger.warning("No GEMINI_API_KEY set. GeminiService will run in mock/fallback mode.")
            self._client = None

    @property
    def is_configured(self) -> bool:
        """Return True if Gemini client is active and configured."""
        return self._client is not None

    def execute_chat_turn(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        context_prompt: str = "",
        conversation_id: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> Tuple[str, List[ToolCallInfo]]:
        """Run an end-to-end reasoning turn:

        1. Format system instructions and memory context.
        2. Format conversation history into GenAI types.Content.
        3. Bind registered tools.
        4. Send message to Gemini.
        5. Intercept and execute any tool function calls via ToolManager.
        6. Return the synthesized natural language response and executed tool records.
        """
        # If client is not available or mock provider is forced, use mock handler
        if not self._client or self.settings.DEFAULT_LLM_PROVIDER.lower() == "mock":
            return self._handle_mock_response(user_message, conversation_id, db)

        # Build full system instruction
        combined_system = SYSTEM_PROMPT
        if context_prompt:
            combined_system += f"\n{context_prompt}"

        # Build GenAI tools
        gemini_tools = self.registry.get_gemini_tools()

        # Build message history for the session
        contents_history: List[types.Content] = []
        for msg in conversation_history:
            role = "user" if msg["role"] == "user" else "model"
            if msg.get("content"):
                contents_history.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["content"])],
                    )
                )

        executed_tool_calls: List[ToolCallInfo] = []

        try:
            config = types.GenerateContentConfig(
                system_instruction=combined_system,
                tools=gemini_tools if gemini_tools else None,
                temperature=0.2,
            )

            chat = self._client.chats.create(
                model=self.settings.GEMINI_MODEL,
                config=config,
                history=contents_history,
            )

            # Send user query to initiate turn
            current_response = chat.send_message(user_message)

            # Handle tool calling loop
            max_tool_iterations = 5
            iteration = 0

            while current_response.function_calls and iteration < max_tool_iterations:
                iteration += 1
                function_response_parts: List[types.Part] = []

                for call in current_response.function_calls:
                    tool_name = call.name
                    arguments = call.args or {}

                    # Execute tool via ToolManager
                    tool_call_info = self.tool_manager.execute_tool(
                        tool_name=tool_name,
                        arguments=arguments,
                        conversation_id=conversation_id,
                        db=db,
                    )
                    executed_tool_calls.append(tool_call_info)

                    # Return result part to Gemini
                    part = types.Part.from_function_response(
                        name=tool_name,
                        response={"result": tool_call_info.result},
                    )
                    function_response_parts.append(part)

                # Send function responses back to continue dialog
                current_response = chat.send_message(function_response_parts)

            final_text = current_response.text or "I have processed your request."
            return final_text, executed_tool_calls

        except Exception as e:
            err_str = str(e)
            logger.error(f"Gemini API error during chat turn: {err_str}", exc_info=True)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                logger.warning("Gemini API rate limit or quota exceeded. Falling back to Standby execution.")
                text, calls = self._handle_mock_response(user_message, conversation_id, db)
                return f"[Standby Mode — API Rate Limit Reached]\n{text}", calls
            raise LLMServiceError(f"Error communicating with Gemini: {err_str}")

    def _handle_mock_response(
        self,
        user_message: str,
        conversation_id: Optional[str],
        db: Optional[Any],
    ) -> Tuple[str, List[ToolCallInfo]]:
        """Mock fallback for offline testing or when API key is missing."""
        lower = user_message.lower()
        tool_calls: List[ToolCallInfo] = []

        if "time" in lower or "date" in lower or "clock" in lower or "day" in lower:
            info = self.tool_manager.execute_tool(
                "get_current_time", {}, conversation_id=conversation_id, db=db
            )
            tool_calls.append(info)
            res = info.result or {}
            time_str = res.get("formatted_local", "Unknown time")
            return f"[JARVIS Standby Mode] The current time is {time_str}.", tool_calls

        if any(char in user_message for char in ["+", "-", "*", "/", "^"]) or "calculate" in lower:
            import re
            # Extract simple math expression if possible
            match = re.search(r"[\d\s\+\-\*\/\(\)\.\^]{3,}", user_message)
            expr = match.group(0).strip() if match else "1 + 1"
            info = self.tool_manager.execute_tool(
                "calculator", {"expression": expr}, conversation_id=conversation_id, db=db
            )
            tool_calls.append(info)
            res = info.result or {}
            ans = res.get("result", "Error")
            return f"[JARVIS Standby Mode] Result: {expr} = {ans}", tool_calls

        return (
            f"[JARVIS Standby Mode] Received your message: '{user_message}'. "
            "Gemini API key is not configured or standby mode is active.",
            tool_calls,
        )


# Global singleton GeminiService
gemini_service = GeminiService()
