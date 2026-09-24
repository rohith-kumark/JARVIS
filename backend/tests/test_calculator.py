"""Tests for the safe AST calculator tool."""

import pytest
from backend.app.core.exceptions import ToolSecurityError
from backend.app.tools.builtin.calculator import CalculatorTool


def test_basic_arithmetic():
    calc = CalculatorTool()

    assert calc.execute("2 + 2")["result"] == 4
    assert calc.execute("10 - 4")["result"] == 6
    assert calc.execute("6 * 7")["result"] == 42
    assert calc.execute("10 / 2")["result"] == 5
    assert calc.execute("10 // 3")["result"] == 3
    assert calc.execute("10 % 3")["result"] == 1
    assert calc.execute("2 ** 8")["result"] == 256


def test_complex_expressions():
    calc = CalculatorTool()

    assert calc.execute("(5 + 3) * (10 - 2)")["result"] == 64
    assert calc.execute("-5 + 15")["result"] == 10
    assert calc.execute("-(4 * 5)")["result"] == -20
    assert calc.execute("3.5 * 2")["result"] == 7


def test_division_by_zero():
    calc = CalculatorTool()

    with pytest.raises(ValueError, match="zero"):
        calc.execute("10 / 0")

    with pytest.raises(ValueError, match="zero"):
        calc.execute("5 // 0")

    with pytest.raises(ValueError, match="zero"):
        calc.execute("7 % 0")


def test_security_blocks_code_execution():
    calc = CalculatorTool()

    # Block imports
    with pytest.raises(ToolSecurityError):
        calc.execute("__import__('os').system('echo pwned')")

    # Block builtin function calls
    with pytest.raises(ToolSecurityError):
        calc.execute("open('/etc/passwd').read()")

    # Block variable access
    with pytest.raises(ToolSecurityError):
        calc.execute("x + 1")

    # Block string evaluation
    with pytest.raises(ToolSecurityError):
        calc.execute("'hello' + 'world'")

    # Block attribute lookups
    with pytest.raises(ToolSecurityError):
        calc.execute("(1).__class__.__bases__")


def test_dos_exponentiation_guard():
    calc = CalculatorTool()

    with pytest.raises(ValueError, match="exceed"):
        calc.execute("9 ** 999999")
