from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import httpx

from app.core.config import settings
from app.routers.chat import router as chat_router
from app.routers.drafts import router as drafts_router
from app.routers.tasks import router as tasks_router
from app.routers.followup import router as followup_router

app = FastAPI(title="MOS Backend")
app.include_router(chat_router)
app.include_router(drafts_router)
app.include_router(tasks_router)
app.include_router(followup_router)

scheduler = AsyncIOScheduler(timezone=settings.TZ)

def _hhmm_to_cron(hhmm: str):
    h, m = hhmm.split(":")
    return int(m), int(h)

@app.on_event("startup")
async def startup():
    # 自分自身のAPIを叩く（Phase1の手抜き実装。後で内部関数呼び出しに置換可）
    async def hit(slot: str):
        async with httpx.AsyncClient() as client:
            await client.post("http://localhost:8000/api/followup/run", params={"slot": slot}, timeout=30)

    m, h = _hhmm_to_cron(settings.FOLLOWUP_MORNING)
    scheduler.add_job(hit, CronTrigger(hour=h, minute=m), args=["morning"], id="followup_morning")

    m, h = _hhmm_to_cron(settings.FOLLOWUP_NOON)
    scheduler.add_job(hit, CronTrigger(hour=h, minute=m), args=["noon"], id="followup_noon")

    m, h = _hhmm_to_cron(settings.FOLLOWUP_EVENING)
    scheduler.add_job(hit, CronTrigger(hour=h, minute=m), args=["evening"], id="followup_evening")

    scheduler.start()
