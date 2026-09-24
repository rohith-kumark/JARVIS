import os
import platform
from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import BaseModel, Field

from backend.app.tools.base import BaseTool, PermissionLevel, ToolCategory
from backend.app.tools.registry import register_tool


class SystemInfoArgs(BaseModel):
    include_environment: bool = Field(
        default=False,
        description="Whether to include safe environment details like Python version and architecture"
    )


@register_tool
class SystemInfoTool(BaseTool):
    """
    Tool to retrieve runtime system health, local timestamp, and OS platform information.
    Read-only inspection tool.
    """
    name = "system_info"
    description = (
        "Get runtime host system information including current local timestamp, system status, "
        "operating system platform, Python version, CPU cores, and system architecture."
    )
    permission_level = PermissionLevel.READ_ONLY
    category = ToolCategory.SYSTEM
    args_schema = SystemInfoArgs
    timeout_seconds = 5.0

    async def _run(self, include_environment: bool = False) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "status": "operational",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "os_name": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
            "cpu_cores": os.cpu_count() or 1,
        }

        if include_environment:
            info["python_version"] = platform.python_version()
            info["architecture"] = platform.architecture()[0]

        return info


@register_tool
class GetSystemInfoAliasTool(SystemInfoTool):
    """Alias for backwards compatibility with get_system_info."""
    name = "get_system_info"
