import uuid
from sqlalchemy import DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.models.base import Base


class FollowupRun(Base):
    __tablename__ = "followup_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    slot: Mapped[str] = mapped_column(Text, nullable=False)  # morning/noon/evening

    # フォローアップ時の統計情報（JSON形式）
    stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 実行時刻
    executed_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
