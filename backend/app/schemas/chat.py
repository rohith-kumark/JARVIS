from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(description="User prompt or directive")
    session_id: Optional[str] = Field(default=None, description="Conversation session ID")
    caller_permission: str = Field(default="admin", description="Caller permission rank")


class ToolExecutionRecord(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    tool_executions: List[ToolExecutionRecord] = Field(default_factory=list)
    llm_provider: str
