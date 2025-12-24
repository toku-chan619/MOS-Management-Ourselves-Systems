from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.db import SessionLocal

from app.routers.chat import router as chat_router
from app.routers.drafts import router as drafts_router
from app.routers.tasks import router as tasks_router
from app.routers.followup import router as followup_router

from app.routers.reminders import router as reminders_router
from app.routers.notifications import router as notifications_router

from app.services.reminders import scan_deadline_reminders
from app.services.notification_render import render_and_project_in_app

app = FastAPI(title="MOS Backend")

app.include_router(chat_router)
app.include_router(drafts_router)
app.include_router(tasks_router)
app.include_router(followup_router)

app.include_router(reminders_router)
app.include_router(notifications_router)

scheduler = AsyncIOScheduler(timezone=ZoneInfo(settings.TZ))


@app.on_event("startup")
async def startup():
    async def scan_job():
        async with SessionLocal() as db:
            await scan_deadline_reminders(db, limit_new_events=10)

    async def render_job():
        async with SessionLocal() as db:
            await render_and_project_in_app(db)

    scheduler.add_job(
        scan_job,
        IntervalTrigger(minutes=settings.REMINDER_SCAN_INTERVAL_MIN),
        id="deadline_scan",
        max_instances=1,
        coalesce=True,
    )

    # created が溜まったら消化する（Phase1の簡易ワーカー）
    scheduler.add_job(
        render_job,
        IntervalTrigger(minutes=1),
        id="notification_render",
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
