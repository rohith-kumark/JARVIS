import datetime
import zoneinfo
from typing import Any, Dict
from pydantic import BaseModel, Field

from backend.app.tools.base import BaseTool, PermissionLevel, ToolCategory
from backend.app.tools.registry import register_tool


class CurrentTimeArgs(BaseModel):
    timezone: str = Field(
        default="UTC",
        description="IANA timezone identifier, e.g. 'UTC', 'America/New_York', 'Europe/London', 'Asia/Kolkata', 'Asia/Tokyo', or 'local'"
    )


@register_tool
class CurrentTimeTool(BaseTool):
    """
    Tool to retrieve the current date, time, and timezone information.
    Read-only inspection tool.
    """
    name = "get_current_time"
    description = (
        "Retrieve the current date, time, day of the week, and UTC offset for a specified timezone. "
        "Default timezone is 'UTC'. Supports standard IANA timezones and 'local'."
    )
    permission_level = PermissionLevel.READ_ONLY
    category = ToolCategory.READ_ONLY
    args_schema = CurrentTimeArgs

    async def _run(self, timezone: str = "UTC") -> Dict[str, Any]:
        tz_str = timezone.strip()

        if tz_str.lower() == "local":
            now = datetime.datetime.now().astimezone()
            tz_name = str(now.tzinfo)
        else:
            try:
                tz = zoneinfo.ZoneInfo(tz_str)
                now = datetime.datetime.now(tz)
                tz_name = tz_str
            except (zoneinfo.ZoneInfoNotFoundError, ValueError) as exc:
                raise ValueError(
                    f"Invalid timezone identifier '{tz_str}'. "
                    f"Please provide a valid IANA timezone (e.g. 'UTC', 'America/New_York', 'Asia/Kolkata')."
                ) from exc

        return {
            "timezone": tz_name,
            "iso_8601": now.isoformat(),
            "formatted": now.strftime("%A, %B %d, %Y, %I:%M:%S %p %Z"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": now.strftime("%A"),
            "utc_offset": now.strftime("%z"),
            "unix_timestamp": int(now.timestamp()),
        }
