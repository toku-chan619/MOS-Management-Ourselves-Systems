from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.db import get_db
from app.models.notification_event import NotificationEvent
from app.services.notification_render import render_and_project_in_app

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.post("/render")
async def render(db: AsyncSession = Depends(get_db)):
    n = await render_and_project_in_app(db)
    return {"rendered": n}


@router.get("")
async def list_events(status: str = "rendered", limit: int = 50, db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(NotificationEvent)
            .where(NotificationEvent.status == status)
            .order_by(NotificationEvent.created_at.desc())
            .limit(min(limit, 200))
        )
    ).scalars().all()

    return [
        {
            "id": str(r.id),
            "kind": r.kind,
            "task_id": str(r.task_id) if r.task_id else None,
            "stage": r.stage,
            "slot": r.slot,
            "since": r.since,
            "status": r.status,
            "created_at": r.created_at,
            "rendered_at": r.rendered_at,
            "rendered_text": r.rendered_text,
        }
        for r in rows
    ]
