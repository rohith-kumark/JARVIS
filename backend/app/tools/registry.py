import importlib
import logging
import pkgutil
from typing import Callable, Dict, List, Optional, Type
from backend.app.core.exceptions import ToolNotFoundError
from backend.app.tools.base import BaseTool, PermissionLevel, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all executable tools in JARVIS.
    Decouples tool definition from orchestrator and API routes.
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> BaseTool:
        """Register an instantiated BaseTool."""
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Tool must inherit from BaseTool, got {type(tool)}")

        if tool.name in self._tools:
            logger.warning(f"Overwriting existing tool registration: '{tool.name}'")

        self._tools[tool.name] = tool
        logger.info(f"Registered tool: '{tool.name}' [Permission: {tool.permission_level.value}]")
        return tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve tool by name."""
        return self._tools.get(name)

    def get_or_fail(self, name: str) -> BaseTool:
        """Retrieve tool by name or raise ToolNotFoundError."""
        tool = self.get(name)
        if tool is None:
            raise ToolNotFoundError(f"Tool '{name}' not found in registry")
        return tool

    def list_tools(self, max_permission: Optional[PermissionLevel] = None) -> List[BaseTool]:
        """List all tools, optionally filtered by permission clearance."""
        if max_permission is None:
            return list(self._tools.values())
        return [tool for tool in self._tools.values() if max_permission.permits(tool.permission_level)]

    def get_function_declarations(self, max_permission: Optional[PermissionLevel] = None) -> List[Dict]:
        """Return list of LLM function declarations for registered tools."""
        tools = self.list_tools(max_permission=max_permission)
        return [tool.to_function_declaration() for tool in tools]

    async def execute(
        self,
        name: str,
        arguments: Optional[Dict] = None,
        caller_permission: PermissionLevel = PermissionLevel.ADMIN,
    ) -> ToolResult:
        """Execute a tool by name with arguments and permission clearance."""
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' is not registered in JARVIS tool registry",
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
        except Exception as exc:
            logger.error(f"Error auto-discovering builtin tools: {exc}", exc_info=True)


# Global singleton tool registry instance
registry = ToolRegistry()


def register_tool(cls: Type[BaseTool]) -> Type[BaseTool]:
    """Class decorator to instantiate and register a tool automatically upon module import."""
    instance = cls()
    registry.register(instance)
    return cls
