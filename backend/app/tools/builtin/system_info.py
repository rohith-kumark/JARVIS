import os
import platform
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.app.tools.base import BaseTool, PermissionLevel
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
    """
    name = "get_system_info"
    description = (
        "Get runtime system information including current local timestamp, system status, "
        "operating system platform, Python version, and system architecture."
    )
    permission_level = PermissionLevel.READ_ONLY
    args_schema = SystemInfoArgs

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
