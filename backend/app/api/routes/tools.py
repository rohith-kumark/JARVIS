import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from backend.app.schemas.tool import (
    ToolExecuteRequest,
    ToolExecuteResponse,
    ToolInfoResponse,
    ToolListResponse,
)
from backend.app.tools.base import PermissionLevel
from backend.app.tools.registry import registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["Tools"])


@router.get("", response_model=ToolListResponse)
async def list_tools(
    permission: Optional[str] = Query(
        default=None,
        description="Filter tools accessible up to this permission level"
    )
) -> ToolListResponse:
    """List all registered tools with their descriptions, parameters, and permission levels."""
    perm_level = None
    if permission:
        try:
            perm_level = PermissionLevel(permission.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid permission level: {permission}")

    tools = registry.list_tools(max_permission=perm_level)
    tool_infos = [
        ToolInfoResponse(
            name=t.name,
            description=t.description,
            permission_level=t.permission_level.value,
            parameters=t.get_input_schema(),
        )
        for t in tools
    ]
    return ToolListResponse(tools=tool_infos, total=len(tool_infos))


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(request: ToolExecuteRequest) -> ToolExecuteResponse:
    """Manually invoke a registered tool with controlled permission check."""
    try:
        caller_perm = PermissionLevel(request.caller_permission.lower())
    except ValueError:
        caller_perm = PermissionLevel.READ_ONLY

    result = await registry.execute(
        name=request.name,
        arguments=request.arguments,
        caller_permission=caller_perm,
    )

    return ToolExecuteResponse(
        name=request.name,
        success=result.success,
        data=result.data,
        error=result.error,
        metadata=result.metadata,
    )
