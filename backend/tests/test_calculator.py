import pytest
from backend.app.tools.builtin.calculator import CalculatorTool
from backend.app.tools.base import PermissionLevel


@pytest.fixture
def calc_tool():
    return CalculatorTool()


@pytest.mark.asyncio
async def test_calculator_basic_arithmetic(calc_tool):
    """Test basic arithmetic calculations with proper precedence."""
    res1 = await calc_tool.execute(expression="2 + 2 * 10")
    assert res1.success is True
    assert res1.data["result"] == 22

    res2 = await calc_tool.execute(expression="(100 - 25) / 5")
    assert res2.success is True
    assert res2.data["result"] == 15

    res3 = await calc_tool.execute(expression="17 % 5")
    assert res3.success is True
    assert res3.data["result"] == 2

    res4 = await calc_tool.execute(expression="2 ** 8")
    assert res4.success is True
    assert res4.data["result"] == 256


@pytest.mark.asyncio
async def test_calculator_math_functions_and_constants(calc_tool):
    """Test standard mathematical functions and constants."""
    res1 = await calc_tool.execute(expression="sqrt(144) + 12")
    assert res1.success is True
    assert res1.data["result"] == 24

    res2 = await calc_tool.execute(expression="abs(-42) + sin(0)")
    assert res2.success is True
    assert res2.data["result"] == 42

    res3 = await calc_tool.execute(expression="log10(100)")
    assert res3.success is True
    assert res3.data["result"] == 2

    res4 = await calc_tool.execute(expression="round(pi, 4)")
    assert res4.success is True
    assert res4.data["result"] == 3.1416


@pytest.mark.asyncio
async def test_calculator_zero_division(calc_tool):
    """Test that zero division is safely caught without crashing."""
    res = await calc_tool.execute(expression="100 / 0")
    assert res.success is False
    assert "division or modulo by zero" in res.error.lower()


@pytest.mark.asyncio
async def test_calculator_arbitrary_code_injection_prevention(calc_tool):
    """
    CRITICAL SECURITY TEST:
    Verify that arbitrary Python code execution attempts are strictly blocked.
    """
    injection_payloads = [
        "__import__('os').system('echo pwned')",
        "open('/etc/passwd').read()",
        "eval('2 + 2')",
        "exec('x = 1')",
        "globals()",
        "locals()",
        "__builtins__",
        "import os",
        "[x for x in [1, 2]]",
        "lambda x: x + 1",
    ]

    for payload in injection_payloads:
        res = await calc_tool.execute(expression=payload)
        assert res.success is False, f"Payload should have been rejected: {payload}"
        assert (
            "forbidden" in res.error.lower()
            or "invalid" in res.error.lower()
            or "undefined" in res.error.lower()
            or "syntax" in res.error.lower()
        )


@pytest.mark.asyncio
async def test_calculator_dos_large_power_prevention(calc_tool):
    """Verify denial of service prevention against astronomically large powers."""
    res = await calc_tool.execute(expression="2 ** 100000")
    assert res.success is False
    assert "exceeds safe computational limits" in res.error.lower()
