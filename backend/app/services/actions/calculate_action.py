"""
Calculation and conversion action.
"""
import math
import re
from typing import Dict, Any

from app.services.actions.base import ActionExecutor, ActionResult
from app.services.actions.registry import action_registry
from app.core.logging import logger


@action_registry.register("calculate")
class CalculateAction(ActionExecutor):
    """
    Perform calculations or unit conversions.

    Parameters:
        expression: Math expression to evaluate (e.g., "2 + 2", "sqrt(16)")
        or
        convert_from: Value and unit to convert from (e.g., "100 USD")
        convert_to: Unit to convert to (e.g., "JPY")
    """

    SAFE_FUNCTIONS = {
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'sum': sum,
        'sqrt': math.sqrt,
        'pow': pow,
        'log': math.log,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'pi': math.pi,
        'e': math.e,
    }

    def validate_parameters(self) -> None:
        """Validate parameters."""
        has_expression = "expression" in self.parameters
        has_conversion = "convert_from" in self.parameters and "convert_to" in self.parameters

        if not (has_expression or has_conversion):
            raise ValueError("Must provide either 'expression' or 'convert_from' and 'convert_to'")

    def _safe_eval(self, expression: str) -> float:
        """Safely evaluate a math expression."""
        # Remove any potentially dangerous characters
        if any(char in expression for char in ['_', '__', 'import', 'exec', 'eval']):
            raise ValueError("Invalid expression")

        # Replace function names with safe implementations
        for func_name in self.SAFE_FUNCTIONS:
            expression = re.sub(
                r'\b' + func_name + r'\b',
                f'SAFE_FUNCTIONS["{func_name}"]',
                expression
            )

        try:
            # Evaluate in restricted namespace
            result = eval(
                expression,
                {"__builtins__": {}, "SAFE_FUNCTIONS": self.SAFE_FUNCTIONS},
                {}
            )
            return float(result)
        except Exception as e:
            raise ValueError(f"Cannot evaluate expression: {e}")

    async def execute(self) -> ActionResult:
        """Perform calculation."""
        try:
            if "expression" in self.parameters:
                # Math calculation
                expression = self.parameters["expression"]
                result = self._safe_eval(expression)

                logger.info(f"Calculated: {expression} = {result}")

                return ActionResult(
                    success=True,
                    data={
                        "expression": expression,
                        "result": result
                    }
                )

            elif "convert_from" in self.parameters:
                # Unit conversion
                convert_from = self.parameters["convert_from"]
                convert_to = self.parameters["convert_to"]

                # Note: In production, use a conversion library like pint
                # For now, just return placeholder

                logger.info(f"Conversion: {convert_from} to {convert_to}")

                return ActionResult(
                    success=True,
                    data={
                        "convert_from": convert_from,
                        "convert_to": convert_to,
                        "note": "Unit conversion not implemented. Use a library like 'pint' in production."
                    }
                )

        except Exception as e:
            logger.error(f"Calculation error: {e}")
            return ActionResult(
                success=False,
                error=str(e)
            )

    async def dry_run(self) -> ActionResult:
        """Simulate calculation."""
        try:
            if "expression" in self.parameters:
                result = self._safe_eval(self.parameters["expression"])
                return ActionResult(
                    success=True,
                    data={
                        "dry_run": True,
                        "expression": self.parameters["expression"],
                        "result": result
                    }
                )
            else:
                return ActionResult(
                    success=True,
                    data={
                        "dry_run": True,
                        "convert_from": self.parameters.get("convert_from"),
                        "convert_to": self.parameters.get("convert_to"),
                        "message": "Would perform conversion"
                    }
                )
        except Exception as e:
            return ActionResult(
                success=False,
                error=str(e)
            )

    def get_description(self) -> str:
        """Get action description."""
        if "expression" in self.parameters:
            return f"Calculate: {self.parameters['expression']}"
        else:
            return f"Convert {self.parameters.get('convert_from')} to {self.parameters.get('convert_to')}"

    def get_safety_warnings(self) -> list[str]:
        """Get safety warnings."""
        return []  # Calculations are safe
