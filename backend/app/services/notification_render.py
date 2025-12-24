from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert

from app.core.config import settings
from app.models.notification_event import NotificationEvent
from app.models.notification_delivery import NotificationDelivery
from app.models.message import Message
from app.services.llm import call_llm_json


def _tz() -> ZoneInfo:
    return ZoneInfo(settings.TZ)


REMINDER_SYSTEM_PROMPT = """
You write a deadline reminder announcement for a personal task manager.
Return ONLY JSON: {"text": "..."}.

Requirements (style A):
- Make it actionable: include a "next step" that can be done in ~15 minutes.
- Ask at most ONE clarification question, only if needed.
- Be concise but specific.
- Use Japanese.
""".strip()

FOLLOWUP_SYSTEM_PROMPT = """
You write a short follow-up summary (morning/noon/evening) for a personal task manager.
Return ONLY JSON: {"text": "..."}.
Use Japanese. Be concise, prioritize urgent items, avoid repetition.
""".strip()


async def _render_event_text(ev: NotificationEvent) -> str:
    payload_text = json.dumps(ev.payload, ensure_ascii=False)

    if ev.kind == "task_deadline_reminder":
        raw = await call_llm_json(REMINDER_SYSTEM_PROMPT, payload_text)
        return str(raw.get("text", "")).strip()

    if ev.kind == "followup_summary":
        raw = await call_llm_json(FOLLOWUP_SYSTEM_PROMPT, payload_text)
        return str(raw.get("text", "")).strip()

    return ""


async def render_and_project_in_app(db: AsyncSession, batch_size: int | None = None) -> int:
    """
    status=created の NotificationEvent をレンダリングし、
    notification_deliveries(in_app) と messages(assistant,event_id=...) を作る。
    """
    if batch_size is None:
        batch_size = settings.RENDER_BATCH_SIZE

    events = (
        await db.execute(
            select(NotificationEvent)
            .where(NotificationEvent.status == "created")
            .order_by(NotificationEvent.created_at.asc())
            .limit(batch_size)
        )
    ).scalars().all()

    processed = 0
    now = datetime.now(tz=_tz())

    for ev in events:
        try:
            text = await _render_event_text(ev)
            if not text:
                raise RuntimeError("empty rendered text")

            # update event
            await db.execute(
                update(NotificationEvent)
                .where(NotificationEvent.id == ev.id)
                .values(status="rendered", rendered_text=text, rendered_at=now)
            )

            # delivery (Phase1: in_app only)
            await db.execute(
                insert(NotificationDelivery).values(
                    event_id=ev.id,
                    channel="in_app",
                    status="sent",
                    sent_at=now,
                )
            )

            # project to messages (uniq index on messages.event_id recommended)
            await db.execute(
                insert(Message).values(
                    role="assistant",
                    content=text,
                    event_id=ev.id,
                )
            )

            processed += 1

        except Exception:
            # mark failed (kept for inspection / later retry policy)
            await db.execute(
                update(NotificationEvent)
                .where(NotificationEvent.id == ev.id)
                .values(status="failed")
            )

    await db.commit()
    return processed
