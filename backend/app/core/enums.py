"""Enums for MOS application"""

from enum import Enum


class TaskStatus(str, Enum):
    """Task status enumeration"""
    BACKLOG = "backlog"
    DOING = "doing"
    WAITING = "waiting"
    DONE = "done"
    CANCELED = "canceled"


class TaskPriority(str, Enum):
    """Task priority enumeration"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class DraftStatus(str, Enum):
    """Task draft status enumeration"""
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class MessageRole(str, Enum):
    """Message role enumeration"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class NotificationEventKind(str, Enum):
    """Notification event kind enumeration"""
    TASK_DEADLINE_REMINDER = "task_deadline_reminder"
    FOLLOWUP_SUMMARY = "followup_summary"


class NotificationEventStatus(str, Enum):
    """Notification event status enumeration"""
    CREATED = "created"
    RENDERED = "rendered"
    FAILED = "failed"


class NotificationChannel(str, Enum):
    """Notification delivery channel enumeration"""
    IN_APP = "in_app"
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    LINE = "line"


class DeliveryStatus(str, Enum):
    """Notification delivery status enumeration"""
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"


class ReminderStage(str, Enum):
    """Reminder stage enumeration"""
    D_MINUS_7 = "D-7"
    D_MINUS_3 = "D-3"
    D_MINUS_1 = "D-1"
    D_0 = "D-0"
    T_MINUS_2H = "T-2H"
    T_MINUS_30M = "T-30M"
    OVERDUE = "OVERDUE"


class FollowupSlot(str, Enum):
    """Followup time slot enumeration"""
    MORNING = "morning"
    NOON = "noon"
    EVENING = "evening"
