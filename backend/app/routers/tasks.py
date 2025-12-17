import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.core.db import get_db
from app.models.task import Task

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.get("/{task_id}/tree")
async def get_task_tree(task_id: str, db: AsyncSession = Depends(get_db)):
    # 存在確認
    t = (await db.execute(select(Task).where(Task.id == uuid.UUID(task_id)))).scalars().first()
    if not t:
        raise HTTPException(404, "task not found")

    q = text("""
    with recursive tree as (
      select * from tasks where id = :root_id
      union all
      select t.* from tasks t
      join tree on t.parent_task_id = tree.id
    )
    select * from tree
    order by parent_task_id nulls first, sort_order, created_at;
    """)
    rows = (await db.execute(q, {"root_id": task_id})).mappings().all()
    return [dict(r) for r in rows]
