from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.config import settings
from app.services.reminders import scan_deadline_reminders

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


@router.post("/scan")
async def scan(db: AsyncSession = Depends(get_db)):
    n = await scan_deadline_reminders(db, limit_new_events=10)
    return {"created_events": n, "interval_min": settings.REMINDER_SCAN_INTERVAL_MIN}
