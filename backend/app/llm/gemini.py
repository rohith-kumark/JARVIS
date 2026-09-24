import logging
from typing import Any, AsyncIterator, Dict, List, Optional
from google import genai
from google.genai import types

from backend.app.core.exceptions import LLMAuthenticationError, LLMException
from backend.app.llm.base import BaseLLMClient, ChatMessage, LLMResponse, MessageRole, ToolCall

logger = logging.getLogger(__name__)


def _dict_to_genai_schema(prop: Dict[str, Any]) -> types.Schema:
    """Converts a JSON Schema dictionary into a google.genai types.Schema."""
    type_str = prop.get("type", "STRING").upper()
    valid_types = {"STRING", "NUMBER", "INTEGER", "BOOLEAN", "ARRAY", "OBJECT"}
    schema_type = type_str if type_str in valid_types else "STRING"

    properties = None
    if "properties" in prop and isinstance(prop["properties"], dict):
        properties = {k: _dict_to_genai_schema(v) for k, v in prop["properties"].items()}

    items = None
    if "items" in prop and isinstance(prop["items"], dict):
        items = _dict_to_genai_schema(prop["items"])

    return types.Schema(
        type=schema_type,
        description=prop.get("description"),
        properties=properties,
        required=prop.get("required"),
        items=items,
    )


class GeminiLLMClient(BaseLLMClient):
    """
    Google Gemini implementation of BaseLLMClient using the official google-genai SDK.
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        if not api_key:
            raise LLMAuthenticationError("GEMINI_API_KEY must be provided")
        self._api_key = api_key
        self._model = model
        try:
            self._client = genai.Client(api_key=self._api_key)
        except Exception as exc:
            raise LLMAuthenticationError(f"Failed to initialize Gemini client: {exc}") from exc

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _convert_messages(self, messages: List[ChatMessage]) -> List[types.Content]:
        """Convert generic ChatMessages into Gemini Contents."""
        contents: List[types.Content] = []
        for msg in messages:
            role = "model" if msg.role == MessageRole.ASSISTANT else "user"
            parts = []

            if msg.content:
                parts.append(types.Part.from_text(text=msg.content))

            if msg.role == MessageRole.TOOL and msg.name:
                parts.append(
                    types.Part.from_function_response(
                        name=msg.name,
                        response={"result": msg.content}
                    )
                )

            if parts:
                contents.append(types.Content(role=role, parts=parts))

        return contents

    def _build_config(
        self,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7
    ) -> types.GenerateContentConfig:
        """Constructs GenerateContentConfig with tools and instructions."""
        tool_objects = []
        if tools:
            func_decls = []
            for t in tools:
                schema = _dict_to_genai_schema(t.get("parameters", {}))
                func_decls.append(
                    types.FunctionDeclaration(
                        name=t["name"],
                        description=t.get("description", ""),
                        parameters=schema,
                    )
                )
            tool_objects.append(types.Tool(function_declarations=func_decls))

        config_args: Dict[str, Any] = {
            "temperature": temperature,
        }
        if tool_objects:
            config_args["tools"] = tool_objects
        if system_instruction:
            config_args["system_instruction"] = system_instruction

        return types.GenerateContentConfig(**config_args)

    async def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate response from Gemini model."""
        try:
            contents = self._convert_messages(messages)
            config = self._build_config(tools=tools, system_instruction=system_instruction, temperature=temperature)

            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )

            tool_calls: List[ToolCall] = []
            text_chunks: List[str] = []

            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.text:
                            text_chunks.append(part.text)
                        if part.function_call:
                            tool_calls.append(
                                ToolCall(
                                    id=part.function_call.name,
                                    name=part.function_call.name,
                                    arguments=dict(part.function_call.args or {}),
                                )
                            )

            final_text = "".join(text_chunks).strip() if text_chunks else None

            return LLMResponse(
                content=final_text,
                tool_calls=tool_calls,
                model=self._model,
                finish_reason="stop",
            )
        except Exception as exc:
            logger.error(f"Gemini API generation error: {exc}", exc_info=True)
            raise LLMException(f"Gemini generation error: {exc}") from exc

    async def generate_stream(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream generated text chunks from Gemini."""
        try:
            contents = self._convert_messages(messages)
            config = self._build_config(tools=tools, system_instruction=system_instruction, temperature=temperature)

            response_stream = await self._client.aio.models.generate_content_stream(
                model=self._model,
                contents=contents,
                config=config,
            )

            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            logger.error(f"Gemini stream error: {exc}", exc_info=True)
            raise LLMException(f"Gemini stream error: {exc}") from exc
