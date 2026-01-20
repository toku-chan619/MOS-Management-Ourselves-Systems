import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from sqlalchemy.exc import SQLAlchemyError
from app.core.db import get_db
from app.core.logging import get_logger
from app.core.enums import DraftStatus
from app.models.draft import TaskDraft
from app.models.task import Task
from app.models.project import Project
from app.schemas.draft import ExtractedDraft

router = APIRouter(prefix="/api/task-drafts", tags=["drafts"])
logger = get_logger(__name__)

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
    """
    Accept a proposed task draft and create actual tasks.

    This endpoint:
    1. Validates the draft exists and is in 'proposed' status
    2. Validates task hierarchy (parent references, depth)
    3. Creates or reuses projects
    4. Creates tasks in proper order (parents before children)
    5. Marks draft as 'accepted'

    All operations are performed in a single transaction for atomicity.
    """
    try:
        draft_uuid = uuid.UUID(draft_id)
    except ValueError:
        raise HTTPException(400, "Invalid draft_id format")

    logger.info("Accepting task draft", draft_id=draft_id)

    try:
        # Fetch draft
        draft = (
            await db.execute(
                select(TaskDraft).where(TaskDraft.id == draft_uuid)
            )
        ).scalars().first()

        if not draft:
            logger.warning("Draft not found", draft_id=draft_id)
            raise HTTPException(404, "Draft not found")

        if draft.status != DraftStatus.PROPOSED.value:
            logger.warning(
                "Draft is not in proposed status",
                draft_id=draft_id,
                status=draft.status
            )
            raise HTTPException(400, f"Draft is not proposed (status: {draft.status})")

        # Parse and validate draft
        try:
            extracted = ExtractedDraft.model_validate(draft.draft_json)
        except Exception as e:
            logger.error(
                "Failed to parse draft JSON",
                draft_id=draft_id,
                error=str(e)
            )
            raise HTTPException(400, f"Invalid draft JSON: {str(e)}")

        # Validate task hierarchy
        temp_ids = {t.temp_id for t in extracted.tasks}
        for t in extracted.tasks:
            if t.parent_temp_id and t.parent_temp_id not in temp_ids:
                logger.error(
                    "Invalid parent reference in draft",
                    draft_id=draft_id,
                    task_temp_id=t.temp_id,
                    parent_temp_id=t.parent_temp_id
                )
                raise HTTPException(
                    400,
                    f"Parent temp_id not found: {t.parent_temp_id}"
                )

        logger.info(
            "Processing draft tasks",
            draft_id=draft_id,
            num_tasks=len(extracted.tasks)
        )

        # Use nested transaction for rollback safety
        async with db.begin_nested():
            project_cache: dict[str, uuid.UUID] = {}
            id_map: dict[str, uuid.UUID] = {}

            # Create tasks in multiple passes (parents first)
            remaining = extracted.tasks[:]
            max_passes = 5

            for pass_num in range(max_passes):
                next_remaining = []
                progressed = False

                for t in remaining:
                    # Check if parent is ready
                    if t.parent_temp_id and t.parent_temp_id not in id_map:
                        next_remaining.append(t)
                        continue

                    # Get or create project
                    proj_id = None
                    if t.project_suggestion:
                        if t.project_suggestion in project_cache:
                            proj_id = project_cache[t.project_suggestion]
                        else:
                            proj_id = await _get_or_create_project(
                                db,
                                t.project_suggestion
                            )
                            if proj_id:
                                project_cache[t.project_suggestion] = proj_id

                    parent_id = (
                        id_map.get(t.parent_temp_id)
                        if t.parent_temp_id
                        else None
                    )

                    # Create task
                    res = await db.execute(
                        insert(Task)
                        .values(
                            project_id=proj_id,
                            parent_task_id=parent_id,
                            title=t.title,
                            description=t.description,
                            status=t.status,
                            priority=t.priority,
                            due_date=t.due_date,
                            due_time=t.due_time,
                            source="chat",
                        )
                        .returning(Task.id)
                    )
                    task_id = res.scalar_one()
                    id_map[t.temp_id] = task_id
                    progressed = True

                    logger.debug(
                        "Created task",
                        temp_id=t.temp_id,
                        task_id=str(task_id),
                        title=t.title
                    )

                remaining = next_remaining
                if not remaining:
                    break

                if not progressed:
                    logger.error(
                        "Could not resolve task hierarchy",
                        draft_id=draft_id,
                        remaining_tasks=len(remaining)
                    )
                    raise HTTPException(
                        400,
                        "Could not resolve task hierarchy (cycle or too deep)"
                    )

            # Mark draft as accepted
            await db.execute(
                update(TaskDraft)
                .where(TaskDraft.id == draft.id)
                .values(status=DraftStatus.ACCEPTED.value)
            )

        # Commit transaction
        await db.commit()

        created_ids = [str(v) for v in id_map.values()]
        logger.info(
            "Draft accepted successfully",
            draft_id=draft_id,
            num_tasks_created=len(created_ids)
        )

        return {"created_task_ids": created_ids}

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            "Database error accepting draft",
            draft_id=draft_id,
            error=str(e)
        )
        raise HTTPException(500, "Database error occurred")

    except Exception as e:
        await db.rollback()
        logger.exception(
            "Unexpected error accepting draft",
            draft_id=draft_id,
            error=str(e)
        )
        raise HTTPException(500, f"Unexpected error: {str(e)}")
