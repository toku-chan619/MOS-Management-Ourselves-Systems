import uuid
from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.models.base import Base

class TaskDraft(Base):
    __tablename__ = "task_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    status: Mapped[str] = mapped_column(Text, nullable=False, default="proposed")  # proposed/accepted/rejected/superseded
    draft_json: Mapped[dict] = mapped_column(nullable=False)  # Uses Base type_annotation_map for JSON/JSONB
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
