from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    """Represents a tool call requested by the model."""
    id: str = Field(default="", description="Unique identifier for the tool call")
    name: str = Field(description="Name of the tool to invoke")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments to pass to the tool")


class ChatMessage(BaseModel):
    """Represents a conversational message in standard format."""
    role: MessageRole
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider."""
    content: Optional[str] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    model: str = ""
    finish_reason: str = "stop"
    usage: Dict[str, int] = Field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class BaseLLMClient(ABC):
    """
    Abstract interface for LLM providers.
    Allows seamlessly swapping Gemini with Claude, OpenAI, or local models.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g., 'gemini', 'mock')."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate a response synchronously or asynchronously."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response tokens as they arrive."""
        pass
