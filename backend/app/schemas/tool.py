from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolInfoResponse(BaseModel):
    name: str = Field(description="Unique tool name")
    description: str = Field(description="Tool functional description")
    permission_level: str = Field(description="Minimum permission level required")
    parameters: Dict[str, Any] = Field(description="JSON Schema of tool arguments")


class ToolListResponse(BaseModel):
    tools: List[ToolInfoResponse]
    total: int


class ToolExecuteRequest(BaseModel):
    name: str = Field(description="Name of tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments to pass to tool")
    caller_permission: str = Field(default="admin", description="Permission level of caller")


class ToolExecuteResponse(BaseModel):
    name: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
