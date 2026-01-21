import uuid
from sqlalchemy import DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.models.base import Base


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # followup_summary / task_deadline_reminder
    kind: Mapped[str] = mapped_column(Text, nullable=False)

    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
    )

    # deadline reminder: D-7/D-3/D-1/D-0/OVERDUE/T-2H/T-30M
    stage: Mapped[str | None] = mapped_column(Text, nullable=True)

    # followup: morning/noon/evening
    slot: Mapped[str | None] = mapped_column(Text, nullable=True)

    # diff-based followup support
    since: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    payload: Mapped[dict] = mapped_column(nullable=False, default=dict)  # Uses Base type_annotation_map
    rendered_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # created/rendered/failed
    status: Mapped[str] = mapped_column(Text, nullable=False, default="created")

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    rendered_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
