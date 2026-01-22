"""
Base classes for task action execution.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from app.core.logging import logger


@dataclass
class ActionResult:
    """Result of action execution."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    executed_at: datetime = None

    def __post_init__(self):
        if self.executed_at is None:
            self.executed_at = datetime.utcnow()


class ActionExecutor(ABC):
    """
    Base class for all action executors.

    Action executors must implement:
    - execute(): Perform the actual action
    - validate_parameters(): Validate action parameters
    - dry_run(): Simulate execution without making changes

    Safety principles:
    1. All actions are logged
    2. User approval required before execution
    3. Dry run available for preview
    4. Execution can be rolled back when possible
    """

    action_type: str = None  # Must be set by subclass

    def __init__(self, parameters: Dict[str, Any]):
        """
        Initialize action executor.

        Args:
            parameters: Action-specific parameters
        """
        self.parameters = parameters
        self.validate_parameters()

    @abstractmethod
    def validate_parameters(self) -> None:
        """
        Validate action parameters.

        Raises:
            ValueError: If parameters are invalid
        """
        pass

    @abstractmethod
    async def execute(self) -> ActionResult:
        """
        Execute the action.

        Returns:
            ActionResult with execution details
        """
        pass

    async def dry_run(self) -> ActionResult:
        """
        Simulate action execution without making actual changes.

        Default implementation logs what would happen.
        Subclasses can override for more detailed simulation.

        Returns:
            ActionResult with simulated execution details
        """
        logger.info(
            f"[DRY RUN] Would execute {self.action_type}",
            parameters=self.parameters
        )
        return ActionResult(
            success=True,
            data={
                "dry_run": True,
                "action_type": self.action_type,
                "parameters": self.parameters,
                "message": "This is a dry run. No actual changes were made."
            }
        )

    def get_description(self) -> str:
        """
        Get human-readable description of what this action will do.

        Returns:
            Description string
        """
        return f"Execute {self.action_type}"

    def get_safety_warnings(self) -> list[str]:
        """
        Get safety warnings for this action.

        Returns:
            List of warning messages
        """
        return []

    def can_rollback(self) -> bool:
        """
        Check if this action can be rolled back.

        Returns:
            True if rollback is possible
        """
        return False

    async def rollback(self) -> ActionResult:
        """
        Roll back this action if possible.

        Returns:
            ActionResult with rollback details
        """
        if not self.can_rollback():
            return ActionResult(
                success=False,
                error="This action cannot be rolled back"
            )
        raise NotImplementedError("Rollback not implemented")
