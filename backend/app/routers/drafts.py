import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from app.core.db import get_db
from app.models.draft import TaskDraft
from app.models.task import Task
from app.models.project import Project
from app.schemas.draft import ExtractedDraft

router = APIRouter(prefix="/api/task-drafts", tags=["drafts"])

@router.get("")
async def list_drafts(status: str = "proposed", db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(TaskDraft).where(TaskDraft.status == status).order_by(TaskDraft.created_at.desc())
    )).scalars().all()

    return [{
        "id": str(r.id),
        "message_id": str(r.message_id),
        "status": r.status,
        "confidence": r.confidence,
        "draft_json": r.draft_json,
        "created_at": r.created_at,
    } for r in rows]

async def _get_or_create_project(db: AsyncSession, name: str | None) -> uuid.UUID | None:
    if not name:
        return None
    existing = (await db.execute(select(Project).where(Project.name == name))).scalars().first()
    if existing:
        return existing.id
    res = await db.execute(insert(Project).values(name=name).returning(Project.id))
    return res.scalar_one()

@router.post("/{draft_id}/accept")
async def accept_draft(draft_id: str, db: AsyncSession = Depends(get_db)):
    draft = (await db.execute(select(TaskDraft).where(TaskDraft.id == uuid.UUID(draft_id)))).scalars().first()
    if not draft:
        raise HTTPException(404, "draft not found")
    if draft.status != "proposed":
        raise HTTPException(400, "draft is not proposed")

    extracted = ExtractedDraft.model_validate(draft.draft_json)

    # 深さ制限や親参照の妥当性チェック（簡易）
    temp_ids = {t.temp_id for t in extracted.tasks}
    for t in extracted.tasks:
        if t.parent_temp_id and t.parent_temp_id not in temp_ids:
            raise HTTPException(400, f"parent_temp_id not found: {t.parent_temp_id}")

    # まずプロジェクト候補をまとめて作る（最初の実装はタスクごとに作ってもOK）
    project_cache: dict[str, uuid.UUID] = {}

    # temp_id -> task_id
    id_map: dict[str, uuid.UUID] = {}

    # 親から作りたいので、親なし→ありの順に複数パスで挿入（シンプル実装）
    remaining = extracted.tasks[:]
    max_passes = 5

    for _ in range(max_passes):
        next_remaining = []
        progressed = False

        for t in remaining:
            if t.parent_temp_id and t.parent_temp_id not in id_map:
                next_remaining.append(t)
                continue

            # project
            proj_id = None
            if t.project_suggestion:
                if t.project_suggestion in project_cache:
                    proj_id = project_cache[t.project_suggestion]
                else:
                    proj_id = await _get_or_create_project(db, t.project_suggestion)
                    project_cache[t.project_suggestion] = proj_id

            parent_id = id_map.get(t.parent_temp_id) if t.parent_temp_id else None

            res = await db.execute(
                insert(Task).values(
                    project_id=proj_id,
                    parent_task_id=parent_id,
                    title=t.title,
                    description=t.description,
                    status=t.status,
                    priority=t.priority,
                    due_date=t.due_date,
                    due_time=t.due_time,
                    source="chat",
                ).returning(Task.id)
            )
            task_id = res.scalar_one()
            id_map[t.temp_id] = task_id
            progressed = True

        remaining = next_remaining
        if not remaining:
            break
        if not progressed:
            raise HTTPException(400, "could not resolve task hierarchy (cycle or too deep)")

    await db.execute(update(TaskDraft).where(TaskDraft.id == draft.id).values(status="accepted"))
    await db.commit()

    return {"created_task_ids": [str(v) for v in id_map.values()]}
