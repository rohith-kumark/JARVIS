import importlib
import logging
import pkgutil
from typing import Callable, Dict, List, Optional, Set, Type
from backend.app.core.exceptions import ToolNotFoundError
from backend.app.tools.base import BaseTool, PermissionLevel, ToolCategory, ToolResult

logger = logging.getLogger(__name__)

# Track all registered tool classes so any ToolRegistry instance can instantiate them
_REGISTERED_TOOL_CLASSES: Set[Type[BaseTool]] = set()


class ToolRegistry:
    """
    Central registry for all executable tools in JARVIS.
    Decouples tool definition from orchestrator and API routes.
    Enforces validation, permission filtering, and safe tool execution.
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> BaseTool:
        """Register an instantiated BaseTool."""
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Tool must inherit from BaseTool, got {type(tool)}")

        if tool.name in self._tools:
            logger.debug(f"Updating tool registration: '{tool.name}'")

        self._tools[tool.name] = tool
        _REGISTERED_TOOL_CLASSES.add(type(tool))
        logger.info(
            f"Registered tool: '{tool.name}' "
            f"[Category: {tool.category.value}, Permission: {tool.permission_level.value}]"
        )
        return tool

    def unregister(self, name: str) -> Optional[BaseTool]:
        """Remove a tool from the registry."""
        return self._tools.pop(name, None)

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve tool by name."""
        return self._tools.get(name)

    def get_or_fail(self, name: str) -> BaseTool:
        """Retrieve tool by name or raise ToolNotFoundError."""
        tool = self.get(name)
        if tool is None:
            raise ToolNotFoundError(f"Tool '{name}' is not registered in JARVIS registry")
        return tool

    def list_tools(
        self,
        max_permission: Optional[PermissionLevel] = None,
        category: Optional[ToolCategory] = None,
    ) -> List[BaseTool]:
        """List all tools, optionally filtered by permission clearance and category."""
        tools = list(self._tools.values())
        if max_permission is not None:
            tools = [t for t in tools if max_permission.permits(t.permission_level)]
        if category is not None:
            tools = [t for t in tools if t.category == category]
        return tools

    def get_function_declarations(
        self,
        max_permission: Optional[PermissionLevel] = None,
        category: Optional[ToolCategory] = None,
    ) -> List[Dict]:
        """Return list of LLM function declarations for registered tools."""
        tools = self.list_tools(max_permission=max_permission, category=category)
        return [tool.to_function_declaration() for tool in tools]

    async def execute(
        self,
        name: str,
        arguments: Optional[Dict] = None,
        caller_permission: PermissionLevel = PermissionLevel.ADMIN,
    ) -> ToolResult:
        """
        Execute a tool by name with arguments and permission clearance.
        Safeguards against unknown tools, invalid inputs, and execution errors.
        """
        tool = self.get(name)
        if tool is None:
            error_msg = f"Unknown tool '{name}' is not registered in JARVIS tool registry"
            logger.warning(f"[Tool Execution Rejected] {error_msg}")
            return ToolResult(
                success=False,
                error=error_msg,
                metadata={"unknown_tool": True, "tool_name": name}
            )

        args = arguments or {}
        return await tool.execute(caller_permission=caller_permission, **args)

    def discover_builtin_tools(self, package_path: str = "backend.app.tools.builtin") -> None:
        """
        Dynamically discovers and loads all modules in the builtin tools package.
        Allows dropping new tools into the builtin folder without modifying orchestrator or registry!
        """
        try:
            package = importlib.import_module(package_path)
            for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
                if not is_pkg and not module_name.startswith("_"):
                    full_name = f"{package_path}.{module_name}"
                    logger.debug(f"Auto-discovering tools from: {full_name}")
                    importlib.import_module(full_name)

            # Ensure all registered tool classes exist in this registry instance
            for tool_cls in _REGISTERED_TOOL_CLASSES:
                inst = tool_cls()
                if inst.name not in self._tools:
                    self._tools[inst.name] = inst
        except Exception as exc:
            logger.error(f"Error auto-discovering builtin tools: {exc}", exc_info=True)


# Global singleton tool registry instance
registry = ToolRegistry()


def register_tool(cls: Type[BaseTool]) -> Type[BaseTool]:
    """Class decorator to instantiate and register a tool automatically upon module import."""
    _REGISTERED_TOOL_CLASSES.add(cls)
    instance = cls()
    registry.register(instance)
    return cls
