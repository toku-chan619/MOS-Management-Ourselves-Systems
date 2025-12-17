from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from app.core.db import get_db
from app.schemas.chat import ChatPostIn
from app.models.message import Message
from app.workers.tasks import extract_and_store_draft

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/messages")
async def post_message(payload: ChatPostIn, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        insert(Message).values(role="user", content=payload.content).returning(Message.id)
    )
    message_id = res.scalar_one()
    await db.commit()

    # 非同期で抽出
    extract_and_store_draft.delay(str(message_id), payload.content)

    return {"message_id": str(message_id), "status": "queued"}
