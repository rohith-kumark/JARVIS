import ast
import logging
import math
import operator
from typing import Any, Dict
from pydantic import BaseModel, Field

from backend.app.tools.base import BaseTool, PermissionLevel, ToolCategory
from backend.app.tools.registry import register_tool

logger = logging.getLogger(__name__)

ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

ALLOWED_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
}

ALLOWED_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}


def _safe_evaluate_ast(node: ast.AST) -> float:
    """
    Recursively evaluate an AST expression with strict whitelisting.
    Never executes arbitrary Python or accesses globals/system modules.
    """
    if isinstance(node, ast.Expression):
        return _safe_evaluate_ast(node.body)

    elif isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            raise ValueError("Boolean constants are not allowed in calculations.")
        if isinstance(node.value, int):
            return node.value
        if isinstance(node.value, float):
            return node.value
        raise ValueError(f"Constant of type '{type(node.value).__name__}' is not allowed in calculations.")

    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Operator '{op_type.__name__}' is not allowed.")

        left_val = _safe_evaluate_ast(node.left)
        right_val = _safe_evaluate_ast(node.right)

        # DoS safeguard against astronomical powers
        if op_type is ast.Pow and (abs(right_val) > 10000 or abs(left_val) > 1e100):
            raise ValueError("Exponent or base exceeds safe computational limits.")

        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right_val == 0:
            raise ZeroDivisionError("Division or modulo by zero is undefined.")

        return ALLOWED_OPERATORS[op_type](left_val, right_val)

    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Unary operator '{op_type.__name__}' is not allowed.")
        return ALLOWED_OPERATORS[op_type](_safe_evaluate_ast(node.operand))

    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCTIONS:
            func_name = getattr(node.func, "id", str(node.func))
            raise ValueError(f"Function call to '{func_name}' is forbidden. Only safe math functions are permitted.")

        func = ALLOWED_FUNCTIONS[node.func.id]
        args = [_safe_evaluate_ast(arg) for arg in node.args]
        return func(*args)

    elif isinstance(node, ast.Name):
        if node.id not in ALLOWED_CONSTANTS:
            raise ValueError(f"Variable or identifier '{node.id}' is undefined or forbidden.")
        return ALLOWED_CONSTANTS[node.id]

    else:
        raise ValueError(f"Forbidden or unsupported syntax element: {type(node).__name__}")


class CalculatorArgs(BaseModel):
    expression: str = Field(
        description="Mathematical expression to evaluate, e.g. '2 * (10 + 5)', 'sqrt(144) + 12', '(100 - 25) / 5'"
    )


@register_tool
class CalculatorTool(BaseTool):
    """
    Safely calculates mathematical expressions.
    Safeguards: Uses dedicated AST evaluation without eval/exec to completely prevent arbitrary code execution.
    """
    name = "calculator"
    description = (
        "Perform exact mathematical calculations for arithmetic expressions, powers, percentages, "
        "and standard math functions (sqrt, sin, cos, tan, log, abs, round, ceil, floor, pi, e). "
        "Strictly safe: does not execute arbitrary code."
    )
    permission_level = PermissionLevel.READ_ONLY
    category = ToolCategory.READ_ONLY
    args_schema = CalculatorArgs
    timeout_seconds = 5.0

    async def _run(self, expression: str) -> Dict[str, Any]:
        expr = expression.strip()
        if not expr:
            raise ValueError("Expression cannot be empty.")

        if len(expr) > 500:
            raise ValueError("Expression exceeds maximum length of 500 characters.")

        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as syn_err:
            raise ValueError(f"Invalid mathematical syntax in '{expr}': {syn_err.msg}") from syn_err

        computed_result = _safe_evaluate_ast(tree)

        # Format integer results without unnecessary .0
        if isinstance(computed_result, float) and computed_result.is_integer():
            formatted_result = int(computed_result)
        else:
            formatted_result = round(computed_result, 10)

        return {
            "expression": expr,
            "result": formatted_result,
        }
