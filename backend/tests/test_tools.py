import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.tools.base import BaseTool, PermissionLevel
from backend.app.tools.registry import ToolRegistry, register_tool, registry


class CustomTestTool(BaseTool):
    name = "custom_test_action"
    description = "A custom tool for testing registry"
    permission_level = PermissionLevel.ADMIN

    async def _run(self, factor: int = 2):
        return {"result": 42 * factor}


@pytest.mark.asyncio
async def test_tool_registry_registration_and_execution():
    test_registry = ToolRegistry()
    tool = CustomTestTool()
    test_registry.register(tool)

    assert test_registry.get("custom_test_action") is not None

    # Test permission rejection
    denied = await test_registry.execute(
        "custom_test_action",
        arguments={"factor": 3},
        caller_permission=PermissionLevel.READ_ONLY,
    )
    assert not denied.success
    assert "Permission denied" in denied.error

    # Test authorized execution
    allowed = await test_registry.execute(
        "custom_test_action",
        arguments={"factor": 3},
        caller_permission=PermissionLevel.ADMIN,
    )
    assert allowed.success
    assert allowed.data == {"result": 126}


@pytest.mark.asyncio
async def test_builtin_system_info_tool():
    tool = registry.get("get_system_info")
    assert tool is not None
    assert tool.permission_level == PermissionLevel.READ_ONLY

    result = await tool.execute(caller_permission=PermissionLevel.READ_ONLY, include_environment=True)
    assert result.success
    assert result.data["status"] == "operational"
    assert "os_name" in result.data
    assert "python_version" in result.data


@pytest.mark.asyncio
async def test_tools_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List tools
        res = await client.get("/api/tools")
        assert res.status_code == 200
        tools_data = res.json()
        assert tools_data["total"] >= 1
        assert any(t["name"] == "get_system_info" for t in tools_data["tools"])

        # Execute tool via API
        exec_res = await client.post(
            "/api/tools/execute",
            json={"name": "get_system_info", "arguments": {"include_environment": False}}
        )
        assert exec_res.status_code == 200
        data = exec_res.json()
        assert data["success"] is True
        assert data["data"]["status"] == "operational"
