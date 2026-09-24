import asyncio
import pytest
from pydantic import BaseModel, Field
from backend.app.core.exceptions import ToolNotFoundError
from backend.app.tools.base import BaseTool, PermissionLevel, ToolCategory, ToolResult
from backend.app.tools.registry import ToolRegistry, register_tool, registry


class DummyArgs(BaseModel):
    multiplier: int = Field(description="Multiplier value")
    prefix: str = Field(default="Result", description="Output prefix")


class DummyActionTool(BaseTool):
    name = "dummy_action"
    description = "A dummy action tool for testing"
    permission_level = PermissionLevel.ADMIN
    category = ToolCategory.ACTION
    args_schema = DummyArgs
    timeout_seconds = 2.0

    async def _run(self, multiplier: int, prefix: str = "Result"):
        return f"{prefix}: {10 * multiplier}"


class TimeoutTestTool(BaseTool):
    name = "timeout_tool"
    description = "A tool that intentionally exceeds timeout"
    permission_level = PermissionLevel.READ_ONLY
    timeout_seconds = 0.1

    async def _run(self):
        await asyncio.sleep(0.5)
        return "finished"


class FailingTool(BaseTool):
    name = "failing_tool"
    description = "A tool that raises an unexpected runtime exception"
    permission_level = PermissionLevel.READ_ONLY

    async def _run(self):
        raise RuntimeError("Simulated internal hardware failure")


@pytest.mark.asyncio
async def test_tool_registration():
    """Verify tools can be dynamically registered and unregistered."""
    test_reg = ToolRegistry()
    tool = DummyActionTool()

    registered = test_reg.register(tool)
    assert registered.name == "dummy_action"
    assert test_reg.get("dummy_action") is tool
    assert len(test_reg.list_tools()) == 1

    # Unregister
    test_reg.unregister("dummy_action")
    assert test_reg.get("dummy_action") is None
    assert len(test_reg.list_tools()) == 0


@pytest.mark.asyncio
async def test_tool_lookup():
    """Verify tool lookup by name, permission filtering, and get_or_fail."""
    test_reg = ToolRegistry()
    test_reg.register(DummyActionTool())

    # Direct lookup
    assert test_reg.get("dummy_action") is not None

    # get_or_fail succeeds for registered tool
    tool = test_reg.get_or_fail("dummy_action")
    assert tool.name == "dummy_action"

    # Permission filtering: READ_ONLY should NOT list an ADMIN tool
    read_only_tools = test_reg.list_tools(max_permission=PermissionLevel.READ_ONLY)
    assert len(read_only_tools) == 0

    # Permission filtering: ADMIN clearance should list the tool
    admin_tools = test_reg.list_tools(max_permission=PermissionLevel.ADMIN)
    assert len(admin_tools) == 1


@pytest.mark.asyncio
async def test_invalid_tool():
    """Verify safeguards when attempting to lookup or execute an unknown tool."""
    test_reg = ToolRegistry()

    # get_or_fail raises ToolNotFoundError
    with pytest.raises(ToolNotFoundError):
        test_reg.get_or_fail("non_existent_tool_xyz")

    # execute returns ToolResult failure without crashing
    result = await test_reg.execute("non_existent_tool_xyz", arguments={"test": 123})
    assert result.success is False
    assert "Unknown tool 'non_existent_tool_xyz'" in result.error
    assert result.metadata.get("unknown_tool") is True


@pytest.mark.asyncio
async def test_invalid_arguments():
    """Verify Pydantic schema validation rejects invalid/missing parameters."""
    test_reg = ToolRegistry()
    test_reg.register(DummyActionTool())

    # Missing required argument 'multiplier'
    missing_args_result = await test_reg.execute(
        "dummy_action",
        arguments={"prefix": "Val"},
        caller_permission=PermissionLevel.ADMIN,
    )
    assert missing_args_result.success is False
    assert "validation failed" in missing_args_result.error.lower()
    assert missing_args_result.metadata.get("validation_error") is True

    # Invalid type for 'multiplier' (passing string that cannot be int)
    invalid_type_result = await test_reg.execute(
        "dummy_action",
        arguments={"multiplier": "not_an_integer"},
        caller_permission=PermissionLevel.ADMIN,
    )
    assert invalid_type_result.success is False
    assert "validation failed" in invalid_type_result.error.lower()


@pytest.mark.asyncio
async def test_successful_tool_execution():
    """Verify tool executes cleanly with valid arguments and authorized permissions."""
    test_reg = ToolRegistry()
    test_reg.register(DummyActionTool())

    result = await test_reg.execute(
        "dummy_action",
        arguments={"multiplier": 5, "prefix": "Total"},
        caller_permission=PermissionLevel.ADMIN,
    )
    assert result.success is True
    assert result.data == "Total: 50"
    assert result.metadata["tool_name"] == "dummy_action"
    assert result.metadata["execution_time_ms"] >= 0


@pytest.mark.asyncio
async def test_tool_failure_handling():
    """Verify exception isolation, timeout safeguard, and permission rejection."""
    test_reg = ToolRegistry()
    test_reg.register(DummyActionTool())
    test_reg.register(TimeoutTestTool())
    test_reg.register(FailingTool())

    # 1. Permission Denied Failure
    perm_denied_result = await test_reg.execute(
        "dummy_action",
        arguments={"multiplier": 2},
        caller_permission=PermissionLevel.READ_ONLY,
    )
    assert perm_denied_result.success is False
    assert "Permission denied" in perm_denied_result.error
    assert perm_denied_result.metadata.get("permission_denied") is True

    # 2. Execution Timeout Failure
    timeout_result = await test_reg.execute(
        "timeout_tool",
        caller_permission=PermissionLevel.READ_ONLY,
    )
    assert timeout_result.success is False
    assert "timed out" in timeout_result.error.lower()
    assert timeout_result.metadata.get("timed_out") is True

    # 3. Internal Exception Handling
    runtime_err_result = await test_reg.execute(
        "failing_tool",
        caller_permission=PermissionLevel.READ_ONLY,
    )
    assert runtime_err_result.success is False
    assert "Simulated internal hardware failure" in runtime_err_result.error
