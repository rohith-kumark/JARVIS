"""Chat endpoint request and response schemas."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload for POST /api/chat."""
    message: str = Field(..., min_length=1, max_length=10000, description="User prompt or instruction")
    conversation_id: Optional[str] = Field(None, description="Optional ID of existing conversation")


class ToolCallInfo(BaseModel):
    """Details of a tool executed during chat orchestration."""
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    status: str = "success"
    execution_time_ms: float = 0.0


class ChatResponse(BaseModel):
    """Payload returned by POST /api/chat."""
    response: str
    conversation_id: str
    tool_calls: List[ToolCallInfo] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
