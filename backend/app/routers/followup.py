from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from app.core.db import get_db
from app.models.message import Message
from app.models.followup_run import FollowupRun
from app.services.followup import build_followup_text

router = APIRouter(prefix="/api/followup", tags=["followup"])

@router.post("/run")
async def run_followup(slot: str, db: AsyncSession = Depends(get_db)):
    text = await build_followup_text(db, slot)
    await db.execute(insert(FollowupRun).values(slot=slot))
    await db.execute(insert(Message).values(role="assistant", content=text))
    await db.commit()
    return {"ok": True, "slot": slot}
