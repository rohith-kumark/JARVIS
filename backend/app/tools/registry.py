"""Dynamic Tool Registry for JARVIS."""

import logging
from typing import Any, Dict, List, Optional
from google.genai import types

from backend.app.tools.base import BaseTool
from backend.app.tools.builtin.calculator import CalculatorTool
from backend.app.tools.builtin.current_time import CurrentTimeTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for discovering, registering, and binding tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance dynamically."""
        if not tool.name:
            raise ValueError(f"Tool {tool.__class__.__name__} must define a unique 'name'")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: '{tool.name}'")

    def unregister(self, name: str) -> Optional[BaseTool]:
        """Unregister a tool by name."""
        tool = self._tools.pop(name, None)
        if tool:
            logger.info(f"Unregistered tool: '{name}'")
        return tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by its unique name."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """Return all currently registered tools."""
        return list(self._tools.values())

    def list_names(self) -> List[str]:
        """Return the names of all registered tools."""
        return list(self._tools.keys())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Return tool definitions as a list of dictionaries for inspection or docs."""
        return [tool.to_dict() for tool in self._tools.values()]

    def get_gemini_tools(self) -> List[types.Tool]:
        """Construct Google GenAI Tool declarations from registered tools."""
        function_declarations: List[types.FunctionDeclaration] = []

        for tool in self._tools.values():
            fd = types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters_json_schema=tool.parameters if tool.parameters else None,
            )
            function_declarations.append(fd)

        if not function_declarations:
            return []

        return [types.Tool(function_declarations=function_declarations)]

    def register_builtins(self) -> None:
        """Register default safe demonstration tools (time, calculator)."""
        self.register(CurrentTimeTool())
        self.register(CalculatorTool())


# Global singleton registry
tool_registry = ToolRegistry()
