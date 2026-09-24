import asyncio
import inspect
import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PermissionLevel(str, Enum):
    """
    Permission levels governing tool invocation security.
    Hierarchical: READ_ONLY (0) < EXECUTE (1) < SENSITIVE (2) < ADMIN (3)
    """
    READ_ONLY = "read_only"
    EXECUTE = "execute"
    SENSITIVE = "sensitive"
    ADMIN = "admin"

    @property
    def level_rank(self) -> int:
        ranks = {
            PermissionLevel.READ_ONLY: 0,
            PermissionLevel.EXECUTE: 1,
            PermissionLevel.SENSITIVE: 2,
            PermissionLevel.ADMIN: 3,
        }
        return ranks[self]

    def permits(self, required: "PermissionLevel") -> bool:
        """Return True if self permission rank meets or exceeds the required permission rank."""
        return self.level_rank >= required.level_rank


class ToolCategory(str, Enum):
    """Categorization separating read-only inspection from external action tools."""
    READ_ONLY = "read_only"
    ACTION = "action"
    SYSTEM = "system"


class ToolResult(BaseModel):
    """Standardized output returned by every tool execution."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class BaseTool(ABC):
    """
    Abstract base class for all JARVIS tools.

    Every tool must implement:
    - name: Unique identifier for the tool.
    - description: Human- and LLM-readable description of what the tool does.
    - permission_level: Security clearance required to execute (READ_ONLY, EXECUTE, SENSITIVE, ADMIN).
    - category: Read-only inspection vs stateful action.
    - args_schema: Optional Pydantic model defining typed input parameters.
    - timeout_seconds: Maximum allowed execution duration before timeout safeguard aborts.
    - _run(): Concrete execution logic (async or sync).
    """
    name: str
    description: str
    permission_level: PermissionLevel = PermissionLevel.READ_ONLY
    category: ToolCategory = ToolCategory.READ_ONLY
    args_schema: Optional[Type[BaseModel]] = None
    timeout_seconds: float = 10.0

    @property
    def is_read_only(self) -> bool:
        return self.permission_level == PermissionLevel.READ_ONLY or self.category == ToolCategory.READ_ONLY

    @abstractmethod
    async def _run(self, **kwargs) -> Any:
        """The tool execution logic implemented by subclasses."""
        pass

    async def execute(
        self,
        caller_permission: PermissionLevel = PermissionLevel.ADMIN,
        **kwargs
    ) -> ToolResult:
        """
        Execute tool with comprehensive safeguards:
        1. Permission hierarchy verification (reject destructive actions without clearance)
        2. Strict argument validation against args_schema
        3. Execution timeout safeguard (prevent hanging processes)
        4. Centralized exception handling & structured telemetry
        """
        start_time = time.perf_counter()

        # 1. Permission Check Safeguard
        if not caller_permission.permits(self.permission_level):
            error_msg = (
                f"Permission denied for tool '{self.name}'. "
                f"Required: {self.permission_level.value}, Caller: {caller_permission.value}"
            )
            logger.warning(
                f"[Tool Security] Unauthorized attempt to invoke '{self.name}' "
                f"(Required: {self.permission_level.value}, Caller: {caller_permission.value})"
            )
            return ToolResult(
                success=False,
                error=error_msg,
                metadata={
                    "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                    "permission_denied": True,
                    "tool_name": self.name,
                }
            )

        # 2. Argument Validation Safeguard
        validated_args = kwargs
        if self.args_schema is not None:
            try:
                validated_model = self.args_schema(**kwargs)
                validated_args = validated_model.model_dump()
            except Exception as val_err:
                error_msg = f"Argument validation failed for tool '{self.name}': {str(val_err)}"
                logger.warning(f"[Tool Validation Error] {error_msg}")
                return ToolResult(
                    success=False,
                    error=error_msg,
                    metadata={
                        "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                        "validation_error": True,
                        "tool_name": self.name,
                    }
                )

        # 3. Execution with Timeout Safeguard & Error Handling
        logger.info(
            f"[Tool Invocation] Tool: '{self.name}' | Category: {self.category.value} | "
            f"Caller: {caller_permission.value} | Args: {list(validated_args.keys())}"
        )

        try:
            # Wrap execution in coroutine if sync
            if inspect.iscoroutinefunction(self._run):
                run_coro = self._run(**validated_args)
            else:
                run_coro = asyncio.to_thread(self._run, **validated_args)

            # Apply execution timeout safeguard
            raw_result = await asyncio.wait_for(run_coro, timeout=self.timeout_seconds)

            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(f"[Tool Success] Tool '{self.name}' completed in {elapsed_ms}ms")

            return ToolResult(
                success=True,
                data=raw_result,
                metadata={
                    "execution_time_ms": elapsed_ms,
                    "tool_name": self.name,
                    "is_read_only": self.is_read_only,
                }
            )

        except asyncio.TimeoutError:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            error_msg = f"Tool '{self.name}' execution timed out after {self.timeout_seconds} seconds"
            logger.error(f"[Tool Timeout] {error_msg}")
            return ToolResult(
                success=False,
                error=error_msg,
                metadata={
                    "execution_time_ms": elapsed_ms,
                    "tool_name": self.name,
                    "timed_out": True,
                }
            )

        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            error_msg = f"Tool '{self.name}' execution failed: {str(exc)}"
            logger.error(f"[Tool Error] {error_msg}", exc_info=True)
            return ToolResult(
                success=False,
                error=error_msg,
                metadata={
                    "execution_time_ms": elapsed_ms,
                    "tool_name": self.name,
                }
            )

    def get_input_schema(self) -> Dict[str, Any]:
        """Returns JSON Schema representation of input parameters."""
        if self.args_schema is not None:
            return self.args_schema.model_json_schema()
        return {"type": "object", "properties": {}}

    def to_function_declaration(self) -> Dict[str, Any]:
        """Returns tool schema formatted for LLM function calling (Gemini / OpenAI compatible)."""
        schema = self.get_input_schema()
        parameters = {
            "type": "object",
            "properties": schema.get("properties", {}),
            "required": schema.get("required", []),
        }
        return {
            "name": self.name,
            "description": self.description,
            "parameters": parameters,
        }
