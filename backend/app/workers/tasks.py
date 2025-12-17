import asyncio
from sqlalchemy import insert
from app.workers.celery_app import celery_app
from app.core.db import SessionLocal
from app.services.extraction import extract_draft
from app.models.draft import TaskDraft
from app.models.agent_run import AgentRun
from app.core.config import settings

@celery_app.task(name="mos.extract_and_store_draft")
def extract_and_store_draft(message_id: str, user_text: str):
    async def _run():
        draft = await extract_draft(user_text)
        overall_conf = 0.0
        if draft.tasks:
            overall_conf = sum(t.confidence for t in draft.tasks) / len(draft.tasks)

        async with SessionLocal() as db:
            await db.execute(insert(AgentRun).values(
                message_id=message_id,
                prompt_version=settings.PROMPT_VERSION,
                model=settings.LLM_MODEL,
                extracted_json=draft.model_dump(mode="json"),
            ))
            await db.execute(insert(TaskDraft).values(
                message_id=message_id,
                status="proposed",
                draft_json=draft.model_dump(mode="json"),
                confidence=overall_conf,
            ))
            await db.commit()

    asyncio.run(_run())
