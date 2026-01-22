"""
Reminder setting action.
"""
from datetime import datetime, timedelta
from typing import Dict, Any

from app.services.actions.base import ActionExecutor, ActionResult
from app.services.actions.registry import action_registry
from app.core.logging import logger


@action_registry.register("set_reminder")
class SetReminderAction(ActionExecutor):
    """
    Set a reminder for a task.

    Parameters:
        task_id: Task ID to set reminder for
        remind_at: ISO format datetime or relative time (e.g., "1 hour", "tomorrow")
        message: Reminder message
    """

    def validate_parameters(self) -> None:
        """Validate parameters."""
        required = ["task_id", "remind_at"]
        for param in required:
            if param not in self.parameters:
                raise ValueError(f"Missing required parameter: {param}")

    def _parse_relative_time(self, time_str: str) -> datetime:
        """Parse relative time strings like '1 hour', 'tomorrow'."""
        now = datetime.now()

        time_str = time_str.lower().strip()

        # Simple parsing (can be extended)
        if "hour" in time_str:
            hours = int(''.join(filter(str.isdigit, time_str)) or 1)
            return now + timedelta(hours=hours)
        elif "minute" in time_str:
            minutes = int(''.join(filter(str.isdigit, time_str)) or 1)
            return now + timedelta(minutes=minutes)
        elif "day" in time_str:
            days = int(''.join(filter(str.isdigit, time_str)) or 1)
            return now + timedelta(days=days)
        elif time_str == "tomorrow":
            return now + timedelta(days=1)
        else:
            # Try parsing as ISO format
            try:
                return datetime.fromisoformat(time_str)
            except:
                raise ValueError(f"Cannot parse time: {time_str}")

    async def execute(self) -> ActionResult:
        """Set the reminder."""
        try:
            task_id = self.parameters["task_id"]
            remind_at_str = self.parameters["remind_at"]
            message = self.parameters.get("message", "Reminder")

            # Parse remind_at
            if isinstance(remind_at_str, str):
                remind_at = self._parse_relative_time(remind_at_str)
            else:
                remind_at = remind_at_str

            # In production, this would create a reminder in the database
            # and schedule it with APScheduler or Celery

            logger.info(
                f"Reminder set for task {task_id} at {remind_at}",
                task_id=task_id,
                remind_at=remind_at
            )

            return ActionResult(
                success=True,
                data={
                    "task_id": task_id,
                    "remind_at": remind_at.isoformat(),
                    "message": message,
                    "note": "Reminder would be created (reminder system integration pending)"
                }
            )

        except Exception as e:
            logger.error(f"Failed to set reminder: {e}")
            return ActionResult(
                success=False,
                error=str(e)
            )

    async def dry_run(self) -> ActionResult:
        """Simulate reminder setting."""
        try:
            remind_at_str = self.parameters["remind_at"]
            if isinstance(remind_at_str, str):
                remind_at = self._parse_relative_time(remind_at_str)
            else:
                remind_at = remind_at_str

            return ActionResult(
                success=True,
                data={
                    "dry_run": True,
                    "task_id": self.parameters["task_id"],
                    "remind_at": remind_at.isoformat(),
                    "message": self.parameters.get("message", "Reminder"),
                    "note": "This is a preview. Reminder not actually created."
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=str(e)
            )

    def get_description(self) -> str:
        """Get action description."""
        return f"Set reminder for task {self.parameters.get('task_id')} at {self.parameters.get('remind_at')}"

    def can_rollback(self) -> bool:
        """Reminders can be cancelled."""
        return True
