"""Demonstration tool: get_current_time."""

from datetime import datetime, timezone
from typing import Any, Dict
from backend.app.tools.base import BaseTool


class CurrentTimeTool(BaseTool):
    """Tool to retrieve the current date, time, and timezone information."""

    name: str = "get_current_time"
    description: str = (
        "Get the current system date and time. Use this whenever the user asks for "
        "the current time, date, day of the week, or needs a real-time timestamp."
    )
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "timezone_name": {
                "type": "string",
                "description": "Optional timezone name, defaults to 'local' or 'UTC'.",
            }
        },
        "required": [],
    }

    def execute(self, timezone_name: str = "local", **kwargs: Any) -> Dict[str, Any]:
        """Return the current time and date formatted."""
        now_local = datetime.now()
        now_utc = datetime.now(timezone.utc)

        return {
            "iso_local": now_local.isoformat(),
            "iso_utc": now_utc.isoformat(),
            "formatted_local": now_local.strftime("%A, %B %d, %Y %I:%M:%S %p"),
            "formatted_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "year": now_local.year,
            "month": now_local.strftime("%B"),
            "day": now_local.day,
            "day_of_week": now_local.strftime("%A"),
            "time_12h": now_local.strftime("%I:%M:%S %p"),
            "time_24h": now_local.strftime("%H:%M:%S"),
        }
