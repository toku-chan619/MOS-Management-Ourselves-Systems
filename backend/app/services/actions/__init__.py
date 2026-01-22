"""
Task action execution services.
"""
from .base import ActionExecutor, ActionResult
from .registry import action_registry
from .email_action import SendEmailAction
from .web_action import FetchWebInfoAction, SearchWebAction
from .reminder_action import SetReminderAction
from .calculate_action import CalculateAction
from .proposal import propose_actions_for_task, ActionProposal
from .executor import execution_engine, ActionExecutionEngine

__all__ = [
    "ActionExecutor",
    "ActionResult",
    "action_registry",
    "SendEmailAction",
    "FetchWebInfoAction",
    "SearchWebAction",
    "SetReminderAction",
    "CalculateAction",
    "propose_actions_for_task",
    "ActionProposal",
    "execution_engine",
    "ActionExecutionEngine",
]
