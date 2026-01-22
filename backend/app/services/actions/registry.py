"""
Action registry for managing available actions.
"""
from typing import Dict, Type, Optional
from app.services.actions.base import ActionExecutor
from app.core.logging import logger


class ActionRegistry:
    """Registry of available action executors."""

    def __init__(self):
        self._actions: Dict[str, Type[ActionExecutor]] = {}

    def register(self, action_type: str):
        """
        Decorator to register an action executor.

        Usage:
            @action_registry.register("send_email")
            class SendEmailAction(ActionExecutor):
                ...
        """
        def decorator(cls: Type[ActionExecutor]):
            cls.action_type = action_type
            self._actions[action_type] = cls
            logger.info(f"Registered action: {action_type}")
            return cls
        return decorator

    def get(self, action_type: str) -> Optional[Type[ActionExecutor]]:
        """Get action executor class by type."""
        return self._actions.get(action_type)

    def get_executor(self, action_type: str) -> Type[ActionExecutor]:
        """Get an action executor by type, raises if not found."""
        if action_type not in self._actions:
            raise ValueError(f"Unknown action type: {action_type}")
        return self._actions[action_type]

    def list_actions(self) -> list[str]:
        """List all registered action types."""
        return list(self._actions.keys())

    def is_registered(self, action_type: str) -> bool:
        """Check if action type is registered."""
        return action_type in self._actions

    def has_action(self, action_type: str) -> bool:
        """Alias for is_registered."""
        return self.is_registered(action_type)


# Global action registry instance
action_registry = ActionRegistry()
