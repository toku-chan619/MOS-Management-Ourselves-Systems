import uuid
from sqlalchemy import DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.models.base import Base


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notification_events.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Phase1: in_app only (future: email/slack/discord/line)
    channel: Mapped[str] = mapped_column(Text, nullable=False)

    # queued/sent/failed
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")

    destination: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
