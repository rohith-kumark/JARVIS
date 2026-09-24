"""Tool definition and execution schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class ToolDefinition(BaseModel):
    """Schema defining a tool for documentation and LLM binding."""
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolExecutionRecord(BaseModel):
    """Database record representation of a tool execution."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    tool_name: str
    arguments: Optional[str] = None
    result: Optional[str] = None
    status: str
    execution_time_ms: float
    created_at: datetime
