"""Tests for ToolRegistry and ToolManager."""

from typing import Any, Dict
from backend.app.tools.base import BaseTool
from backend.app.tools.manager import ToolManager
from backend.app.tools.registry import ToolRegistry


class EchoTool(BaseTool):
    name = "echo"
    description = "Echo input back"
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    def execute(self, text: str = "", **kwargs: Any) -> Dict[str, Any]:
        return {"echoed": text}


def test_registry_registration():
    reg = ToolRegistry()
    assert len(reg.list_tools()) == 0

    tool = EchoTool()
    reg.register(tool)
    assert reg.get("echo") == tool
    assert "echo" in reg.list_names()

    # Schemas
    schemas = reg.get_schemas()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "echo"

    # Unregister
    reg.unregister("echo")
    assert reg.get("echo") is None


def test_tool_manager_execution():
    reg = ToolRegistry()
    reg.register(EchoTool())
    manager = ToolManager(registry=reg)

    info = manager.execute_tool("echo", {"text": "hello jarvis"})
    assert info.status == "success"
    assert info.result == {"echoed": "hello jarvis"}
    assert info.execution_time_ms >= 0


def test_tool_manager_missing_tool():
    reg = ToolRegistry()
    manager = ToolManager(registry=reg)

    info = manager.execute_tool("nonexistent_tool", {})
    assert info.status == "error"
    assert "not found" in info.result["error"]
