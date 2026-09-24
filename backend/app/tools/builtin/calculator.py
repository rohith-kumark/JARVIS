"""Demonstration tool: safe AST-based calculator.

Never uses eval() or exec(). Only parses and evaluates valid arithmetic AST nodes.
"""

import ast
import operator
from typing import Any, Dict, Union
from backend.app.core.exceptions import ToolSecurityError
from backend.app.tools.base import BaseTool

# Supported binary operators
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# Supported unary operators
SAFE_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class CalculatorTool(BaseTool):
    """Safely evaluates arithmetic expressions using AST parsing."""

    name: str = "calculator"
    description: str = (
        "Safely evaluate a mathematical expression (addition, subtraction, multiplication, "
        "division, integer division, modulo, exponentiation). Example expressions: "
        "'45 * 12', '(100 - 25) / 5', '2 ** 8'. Do not pass Python variables or functions."
    )
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The arithmetic expression to safely compute.",
            }
        },
        "required": ["expression"],
    }

    def _eval_node(self, node: ast.AST) -> Union[int, float]:
        """Recursively evaluate an AST node strictly against safe whitelisted types."""
        if isinstance(node, ast.Expression):
            return self._eval_node(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ToolSecurityError(f"Security error: Disallowed constant type '{type(node.value).__name__}'")

        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in SAFE_OPERATORS:
                raise ToolSecurityError(f"Security error: Disallowed operator '{op_type.__name__}'")

            left = self._eval_node(node.left)
            right = self._eval_node(node.right)

            # Division by zero guard
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ValueError("Math error: Division or modulo by zero")

            # Exponential DoS guard
            if op_type is ast.Pow:
                if abs(right) > 1000 or abs(left) > 1000000:
                    raise ValueError("Math error: Exponentiation operands exceed safe computation limits")

            return SAFE_OPERATORS[op_type](left, right)

        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in SAFE_UNARY_OPERATORS:
                raise ToolSecurityError(f"Security error: Disallowed unary operator '{op_type.__name__}'")
            operand = self._eval_node(node.operand)
            return SAFE_UNARY_OPERATORS[op_type](operand)

        # Explicitly reject calls, names, attributes, imports, subscripts, etc.
        raise ToolSecurityError(
            f"Security error: Disallowed expression syntax '{type(node).__name__}'. "
            "Only pure arithmetic expressions are allowed."
        )

    def execute(self, expression: str, **kwargs: Any) -> Dict[str, Any]:
        """Parse and safely compute the arithmetic expression."""
        if not expression or not expression.strip():
            raise ValueError("Expression cannot be empty")

        cleaned = expression.strip()
        if len(cleaned) > 250:
            raise ValueError("Expression length exceeds maximum allowed length of 250 characters")

        try:
            tree = ast.parse(cleaned, mode="eval")
            result = self._eval_node(tree)
            # If the float has no fractional part, convert to int for cleaner output (e.g. 540.0 -> 540)
            if isinstance(result, float) and result.is_integer():
                result = int(result)

            return {
                "expression": cleaned,
                "result": result,
                "formatted": f"{cleaned} = {result}",
            }
        except (SyntaxError, ValueError, ToolSecurityError) as e:
            raise e
        except Exception as e:
            raise ValueError(f"Failed to evaluate expression: {str(e)}")
