"""Tool Manager for executing, monitoring, and logging tool calls."""

import json
import logging
import time
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from backend.app.core.exceptions import ToolExecutionError, ToolSecurityError
from backend.app.db.models import ToolExecution
from backend.app.schemas.chat import ToolCallInfo
from backend.app.tools.registry import ToolRegistry, tool_registry

logger = logging.getLogger(__name__)


class ToolManager:
    """Handles execution, safety boundaries, timing, and persistence of tool calls."""

    def __init__(self, registry: Optional[ToolRegistry] = None) -> None:
        self.registry = registry or tool_registry

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> ToolCallInfo:
        """Safely execute a tool with timing, exception handling, and database logging."""
        tool = self.registry.get(tool_name)
        start_time = time.perf_counter()

        if not tool:
            err_msg = f"Tool '{tool_name}' not found in registry"
            logger.warning(err_msg)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ToolCallInfo(
                tool_name=tool_name,
                arguments=arguments,
                result={"error": err_msg},
                status="error",
                execution_time_ms=round(elapsed_ms, 2),
            )

        status = "success"
        result_payload: Any = None

        try:
            logger.info(f"Executing tool '{tool_name}' with arguments: {arguments}")
            result_payload = tool.execute(**arguments)
            logger.info(f"Tool '{tool_name}' completed successfully")
        except ToolSecurityError as e:
            status = "error"
            result_payload = {"error": f"Security violation: {e.message}"}
            logger.warning(f"Security error executing tool '{tool_name}': {e.message}")
        except Exception as e:
            status = "error"
            result_payload = {"error": f"Execution error: {str(e)}"}
            logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Persist to database if session provided
        if db:
            try:
                db_record = ToolExecution(
                    conversation_id=conversation_id,
                    message_id=message_id,
                    tool_name=tool_name,
                    arguments=json.dumps(arguments) if arguments else None,
                    result=json.dumps(result_payload) if isinstance(result_payload, (dict, list)) else str(result_payload),
                    status=status,
                    execution_time_ms=round(elapsed_ms, 2),
                )
                db.add(db_record)
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to record tool execution to database: {e}")
                db.rollback()

        return ToolCallInfo(
            tool_name=tool_name,
            arguments=arguments,
            result=result_payload,
            status=status,
            execution_time_ms=round(elapsed_ms, 2),
        )


# Global singleton tool manager
tool_manager = ToolManager()
