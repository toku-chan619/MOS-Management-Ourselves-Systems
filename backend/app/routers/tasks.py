import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, insert, update, delete, and_, func
from sqlalchemy.exc import SQLAlchemyError
from app.core.db import get_db
from app.core.logging import get_logger
from app.core.enums import TaskStatus, TaskPriority
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskTreeNode

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
logger = get_logger(__name__)


@router.get("", response_model=dict)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    project_id: Optional[str] = Query(None, description="Filter by project_id"),
    parent_task_id: Optional[str] = Query(None, description="Filter by parent_task_id (use 'null' for root tasks)"),
    limit: int = Query(50, ge=1, le=100, description="Max number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of tasks with optional filtering and pagination.

    Filters:
    - status: backlog, doing, waiting, done, canceled
    - priority: low, normal, high, urgent
    - project_id: UUID of project
    - parent_task_id: UUID of parent task, or 'null' for root tasks only

    Returns paginated task list with total count.
    """
    try:
        # Build query with filters
        conditions = []

        if status:
            try:
                TaskStatus(status)  # Validate
                conditions.append(Task.status == status)
            except ValueError:
                raise HTTPException(400, f"Invalid status: {status}")

        if priority:
            try:
                TaskPriority(priority)  # Validate
                conditions.append(Task.priority == priority)
            except ValueError:
                raise HTTPException(400, f"Invalid priority: {priority}")

        if project_id:
            try:
                conditions.append(Task.project_id == uuid.UUID(project_id))
            except ValueError:
                raise HTTPException(400, "Invalid project_id format")

        if parent_task_id:
            if parent_task_id.lower() == "null":
                conditions.append(Task.parent_task_id.is_(None))
            else:
                try:
                    conditions.append(Task.parent_task_id == uuid.UUID(parent_task_id))
                except ValueError:
                    raise HTTPException(400, "Invalid parent_task_id format")

        # Count total matching tasks
        count_query = select(func.count()).select_from(Task)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = (await db.execute(count_query)).scalar()

        # Fetch tasks with pagination
        query = select(Task)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(Task.created_at.desc()).limit(limit).offset(offset)

        tasks = (await db.execute(query)).scalars().all()

        logger.info(
            "Listed tasks",
            total=total,
            returned=len(tasks),
            filters={
                "status": status,
                "priority": priority,
                "project_id": project_id,
                "parent_task_id": parent_task_id,
            },
        )

        return {
            "tasks": [TaskResponse.model_validate(t) for t in tasks],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error listing tasks", error=str(e))
        raise HTTPException(500, "Internal server error")


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single task by ID"""
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(400, "Invalid task_id format")

    task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalars().first()

    if not task:
        logger.warning("Task not found", task_id=task_id)
        raise HTTPException(404, "Task not found")

    logger.debug("Retrieved task", task_id=task_id)
    return TaskResponse.model_validate(task)


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(task_data: TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create a new task"""
    try:
        logger.info("Creating task", title=task_data.title)

        # Validate parent task exists if specified
        if task_data.parent_task_id:
            parent = (
                await db.execute(select(Task).where(Task.id == task_data.parent_task_id))
            ).scalars().first()
            if not parent:
                raise HTTPException(404, "Parent task not found")

        # Validate project exists if specified
        if task_data.project_id:
            from app.models.project import Project

            project = (
                await db.execute(select(Project).where(Project.id == task_data.project_id))
            ).scalars().first()
            if not project:
                raise HTTPException(404, "Project not found")

        # Create task
        result = await db.execute(
            insert(Task)
            .values(
                **task_data.model_dump(exclude_unset=True),
                source="manual",
            )
            .returning(Task)
        )
        task = result.scalar_one()
        await db.commit()

        logger.info("Task created successfully", task_id=str(task.id), title=task.title)
        return TaskResponse.model_validate(task)

    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Database error creating task", error=str(e))
        raise HTTPException(500, "Database error occurred")
    except Exception as e:
        await db.rollback()
        logger.exception("Unexpected error creating task", error=str(e))
        raise HTTPException(500, f"Unexpected error: {str(e)}")


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str, task_data: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a task (full update)"""
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(400, "Invalid task_id format")

    try:
        logger.info("Updating task", task_id=task_id)

        # Check task exists
        task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalars().first()
        if not task:
            raise HTTPException(404, "Task not found")

        # Validate parent task if being updated
        if task_data.parent_task_id is not None:
            if task_data.parent_task_id == task_uuid:
                raise HTTPException(400, "Task cannot be its own parent")
            parent = (
                await db.execute(select(Task).where(Task.id == task_data.parent_task_id))
            ).scalars().first()
            if not parent:
                raise HTTPException(404, "Parent task not found")

        # Update task
        update_data = task_data.model_dump(exclude_unset=True)
        if update_data:
            await db.execute(
                update(Task).where(Task.id == task_uuid).values(**update_data)
            )
            await db.commit()

            # Fetch updated task
            task = (
                await db.execute(select(Task).where(Task.id == task_uuid))
            ).scalars().first()

        logger.info("Task updated successfully", task_id=task_id)
        return TaskResponse.model_validate(task)

    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Database error updating task", task_id=task_id, error=str(e))
        raise HTTPException(500, "Database error occurred")
    except Exception as e:
        await db.rollback()
        logger.exception("Unexpected error updating task", task_id=task_id, error=str(e))
        raise HTTPException(500, f"Unexpected error: {str(e)}")


@router.patch("/{task_id}", response_model=TaskResponse)
async def partial_update_task(
    task_id: str, task_data: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    """Partially update a task (same as PUT for this implementation)"""
    return await update_task(task_id, task_data, db)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a task (and its children due to CASCADE)"""
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(400, "Invalid task_id format")

    try:
        logger.info("Deleting task", task_id=task_id)

        # Check task exists
        task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalars().first()
        if not task:
            raise HTTPException(404, "Task not found")

        # Delete task (CASCADE will delete children)
        await db.execute(delete(Task).where(Task.id == task_uuid))
        await db.commit()

        logger.info("Task deleted successfully", task_id=task_id)
        return None

    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Database error deleting task", task_id=task_id, error=str(e))
        raise HTTPException(500, "Database error occurred")
    except Exception as e:
        await db.rollback()
        logger.exception("Unexpected error deleting task", task_id=task_id, error=str(e))
        raise HTTPException(500, f"Unexpected error: {str(e)}")

@router.get("/{task_id}/tree")
async def get_task_tree(task_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get task tree (task and all descendants) using recursive CTE.

    Returns the root task and all its children in a flat list,
    ordered by hierarchy.
    """
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(400, "Invalid task_id format")

    try:
        # Check task exists
        t = (await db.execute(select(Task).where(Task.id == task_uuid))).scalars().first()
        if not t:
            logger.warning("Task not found for tree", task_id=task_id)
            raise HTTPException(404, "Task not found")

        # Recursive CTE to get full tree
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
        rows = (await db.execute(q, {"root_id": str(task_uuid)})).mappings().all()

        logger.info("Retrieved task tree", task_id=task_id, num_tasks=len(rows))
        return [dict(r) for r in rows]

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting task tree", task_id=task_id, error=str(e))
        raise HTTPException(500, "Internal server error")
