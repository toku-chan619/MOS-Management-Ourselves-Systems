"""
Task Action models for automated task execution.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.db import Base


class ActionStatus(str, enum.Enum):
    """Status of an action."""
    PROPOSED = "proposed"      # LLM proposed this action
    APPROVED = "approved"      # User approved, ready to execute
    EXECUTING = "executing"    # Currently being executed
    COMPLETED = "completed"    # Successfully completed
    FAILED = "failed"          # Execution failed
    CANCELLED = "cancelled"    # User cancelled


class ActionType(str, enum.Enum):
    """Types of actions that can be performed."""
    SEND_EMAIL = "send_email"
    FETCH_WEB_INFO = "fetch_web_info"
    SET_REMINDER = "set_reminder"
    CALCULATE = "calculate"
    CREATE_CALENDAR_EVENT = "create_calendar_event"
    SEARCH_WEB = "search_web"


class TaskAction(Base):
    """
    Represents an automated action that can be performed for a task.

    Actions follow a strict approval flow:
    1. LLM proposes action (status=proposed)
    2. User reviews and approves (status=approved)
    3. System executes (status=executing → completed/failed)

    All actions are logged for auditing.
    """
    __tablename__ = "task_actions"

    action_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)

    action_type = Column(SQLEnum(ActionType), nullable=False)
    status = Column(SQLEnum(ActionStatus), nullable=False, default=ActionStatus.PROPOSED)

    # Action parameters (JSON)
    parameters = Column(JSONB, nullable=False, default=dict)

    # LLM reasoning for why this action was proposed
    reasoning = Column(Text)

    # Confidence score from LLM (0.0-1.0)
    confidence = Column(Float, nullable=False, default=0.5)

    # Execution details
    result = Column(JSONB)  # Result of execution
    error_message = Column(Text)  # Error details if failed

    # Dry run flag (if True, simulate execution without actual changes)
    dry_run = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True))
    executed_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # User who approved (future: for multi-user support)
    approved_by = Column(String)

    # Relationship
    task = relationship("Task", back_populates="actions")

    def __repr__(self):
        return f"<TaskAction {self.action_id} type={self.action_type} status={self.status}>"
