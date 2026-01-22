import uuid
from sqlalchemy import Date, Time, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base

# enumはAlembicで作るのが綺麗だが、Phase1はText運用でも可
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    status: Mapped[str] = mapped_column(Text, nullable=False, default="backlog")   # backlog/doing/waiting/done/canceled
    priority: Mapped[str] = mapped_column(Text, nullable=False, default="normal") # low/normal/high/urgent

    due_date: Mapped[object | None] = mapped_column(Date, nullable=True)
    due_time: Mapped[object | None] = mapped_column(Time, nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    source: Mapped[str] = mapped_column(Text, nullable=False, default="chat")

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    actions = relationship("TaskAction", back_populates="task", cascade="all, delete-orphan")
