from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.models.task import Task
from app.models.notification_event import NotificationEvent


STAGES_DATE_ONLY = [
    ("D-7", 7),
    ("D-3", 3),
    ("D-1", 1),
    ("D-0", 0),
]

# due_time ありのみ
STAGES_TIME_ONLY = [
    ("T-2H", timedelta(hours=2)),
    ("T-30M", timedelta(minutes=30)),
]


def _tz() -> ZoneInfo:
    return ZoneInfo(settings.TZ)


def _now() -> datetime:
    return datetime.now(tz=_tz())


def _compute_stages_for_task(t: Task, now: datetime) -> list[str]:
    if t.status in ("done", "canceled"):
        return []

    if t.due_date is None:
        return []

    today = now.date()
    days_left = (t.due_date - today).days

    # overdue (date-based)
    if t.due_date < today:
        return ["OVERDUE"]

    stages: list[str] = []

    for stage, d in STAGES_DATE_ONLY:
        if days_left == d:
            stages.append(stage)

    # time-based (only if due_time exists and due is today)
    if t.due_time is not None and t.due_date == today:
        due_dt = datetime.combine(t.due_date, t.due_time).replace(tzinfo=_tz())
        delta = due_dt - now

        # overdue (time-based)
        if delta.total_seconds() < 0:
            return ["OVERDUE"]

        # if within threshold, stage is eligible
        for stage, th in STAGES_TIME_ONLY:
            if delta <= th:
                stages.append(stage)

    # stable order (optional)
    order = {"OVERDUE": 0, "T-30M": 1, "T-2H": 2, "D-0": 3, "D-1": 4, "D-3": 5, "D-7": 6}
    stages.sort(key=lambda s: order.get(s, 999))
    return stages


async def scan_deadline_reminders(db: AsyncSession, limit_new_events: int = 10) -> int:
    """
    期限接近の NotificationEvent を作成する（冪等）。
    同一 task_id × stage はユニーク制約により重複しない。
    """
    now = _now()

    # Phase1: 広めに取ってPython側で判定（最適化は後で）
    tasks = (
        await db.execute(
            select(Task)
            .where(
                and_(
                    Task.due_date.is_not(None),
                    Task.status.notin_(("done", "canceled")),
                )
            )
            .order_by(Task.due_date.asc())
            .limit(200)
        )
    ).scalars().all()

    created = 0
    for t in tasks:
        stages = _compute_stages_for_task(t, now)
        for stage in stages:
            if created >= limit_new_events:
                break

            payload = {
                "kind": "task_deadline_reminder",
                "stage": stage,
                "now": now.isoformat(),
                "task": {
                    "id": str(t.id),
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "due_time": t.due_time.isoformat() if t.due_time else None,
                },
            }

            stmt = (
                pg_insert(NotificationEvent)
                .values(
                    kind="task_deadline_reminder",
                    task_id=t.id,
                    stage=stage,
                    payload=payload,
                    status="created",
                )
                .on_conflict_do_nothing(index_elements=["task_id", "stage"])
                .returning(NotificationEvent.id)
            )

            res = await db.execute(stmt)
            new_id = res.scalar_one_or_none()
            if new_id is not None:
                created += 1

    if created:
        await db.commit()
    return created
