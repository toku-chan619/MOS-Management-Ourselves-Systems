import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, and_, func
from sqlalchemy.exc import SQLAlchemyError
from app.core.db import get_db
from app.core.logging import get_logger
from app.models.project import Project
from app.models.task import Task
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.schemas.task import TaskResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])
logger = get_logger(__name__)


@router.get("", response_model=dict)
async def list_projects(
    is_archived: Optional[bool] = Query(None, description="Filter by archived status"),
    limit: int = Query(50, ge=1, le=100, description="Max number of projects to return"),
    offset: int = Query(0, ge=0, description="Number of projects to skip"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of projects with optional filtering and pagination.

    Filters:
    - is_archived: true/false to filter by archived status

    Returns paginated project list with total count.
    """
    try:
        # Build query with filters
        conditions = []

        if is_archived is not None:
            conditions.append(Project.is_archived == is_archived)

        # Count total matching projects
        count_query = select(func.count()).select_from(Project)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = (await db.execute(count_query)).scalar()

        # Fetch projects with pagination
        query = select(Project)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(Project.created_at.desc()).limit(limit).offset(offset)

        projects = (await db.execute(query)).scalars().all()

        logger.info(
            "Listed projects",
            total=total,
            returned=len(projects),
            is_archived=is_archived,
        )

        return {
            "projects": [ProjectResponse.model_validate(p) for p in projects],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error listing projects", error=str(e))
        raise HTTPException(500, "Internal server error")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single project by ID"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id format")

    project = (
        await db.execute(select(Project).where(Project.id == project_uuid))
    ).scalars().first()

    if not project:
        logger.warning("Project not found", project_id=project_id)
        raise HTTPException(404, "Project not found")

    logger.debug("Retrieved project", project_id=project_id)
    return ProjectResponse.model_validate(project)


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_data: ProjectCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new project"""
    try:
        logger.info("Creating project", name=project_data.name)

        # Check if project with same name already exists
        existing = (
            await db.execute(select(Project).where(Project.name == project_data.name))
        ).scalars().first()

        if existing:
            logger.warning(
                "Project with name already exists",
                name=project_data.name,
                existing_id=str(existing.id),
            )
            raise HTTPException(409, f"Project with name '{project_data.name}' already exists")

        # Create project
        result = await db.execute(
            insert(Project).values(**project_data.model_dump()).returning(Project)
        )
        project = result.scalar_one()
        await db.commit()

        logger.info(
            "Project created successfully", project_id=str(project.id), name=project.name
        )
        return ProjectResponse.model_validate(project)

    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Database error creating project", error=str(e))
        raise HTTPException(500, "Database error occurred")
    except Exception as e:
        await db.rollback()
        logger.exception("Unexpected error creating project", error=str(e))
        raise HTTPException(500, f"Unexpected error: {str(e)}")


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str, project_data: ProjectUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a project"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id format")

    try:
        logger.info("Updating project", project_id=project_id)

        # Check project exists
        project = (
            await db.execute(select(Project).where(Project.id == project_uuid))
        ).scalars().first()
        if not project:
            raise HTTPException(404, "Project not found")

        # Check name uniqueness if name is being updated
        if project_data.name and project_data.name != project.name:
            existing = (
                await db.execute(select(Project).where(Project.name == project_data.name))
            ).scalars().first()
            if existing:
                raise HTTPException(
                    409, f"Project with name '{project_data.name}' already exists"
                )

        # Update project
        update_data = project_data.model_dump(exclude_unset=True)
        if update_data:
            await db.execute(
                update(Project).where(Project.id == project_uuid).values(**update_data)
            )
            await db.commit()

            # Fetch updated project
            project = (
                await db.execute(select(Project).where(Project.id == project_uuid))
            ).scalars().first()

        logger.info("Project updated successfully", project_id=project_id)
        return ProjectResponse.model_validate(project)

    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Database error updating project", project_id=project_id, error=str(e))
        raise HTTPException(500, "Database error occurred")
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Unexpected error updating project", project_id=project_id, error=str(e)
        )
        raise HTTPException(500, f"Unexpected error: {str(e)}")


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    force: bool = Query(False, description="Force delete even if project has tasks"),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a project (logical delete by archiving).

    By default, archives the project instead of hard delete.
    Use force=true to actually delete the project (will fail if tasks exist).
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id format")

    try:
        logger.info("Deleting project", project_id=project_id, force=force)

        # Check project exists
        project = (
            await db.execute(select(Project).where(Project.id == project_uuid))
        ).scalars().first()
        if not project:
            raise HTTPException(404, "Project not found")

        if force:
            # Check if project has tasks
            task_count = (
                await db.execute(
                    select(func.count()).select_from(Task).where(Task.project_id == project_uuid)
                )
            ).scalar()

            if task_count > 0:
                raise HTTPException(
                    400,
                    f"Cannot delete project with {task_count} task(s). "
                    "Archive the project instead or delete all tasks first.",
                )

            # Hard delete
            await db.execute(delete(Project).where(Project.id == project_uuid))
            logger.info("Project deleted permanently", project_id=project_id)
        else:
            # Logical delete (archive)
            await db.execute(
                update(Project)
                .where(Project.id == project_uuid)
                .values(is_archived=True)
            )
            logger.info("Project archived", project_id=project_id)

        await db.commit()
        return None

    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Database error deleting project", project_id=project_id, error=str(e))
        raise HTTPException(500, "Database error occurred")
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Unexpected error deleting project", project_id=project_id, error=str(e)
        )
        raise HTTPException(500, f"Unexpected error: {str(e)}")


@router.get("/{project_id}/tasks", response_model=dict)
async def get_project_tasks(
    project_id: str,
    status: Optional[str] = Query(None, description="Filter by task status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get all tasks in a project with optional filtering and pagination"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id format")

    try:
        # Check project exists
        project = (
            await db.execute(select(Project).where(Project.id == project_uuid))
        ).scalars().first()
        if not project:
            raise HTTPException(404, "Project not found")

        # Build query
        conditions = [Task.project_id == project_uuid]

        if status:
            from app.core.enums import TaskStatus

            try:
                TaskStatus(status)  # Validate
                conditions.append(Task.status == status)
            except ValueError:
                raise HTTPException(400, f"Invalid status: {status}")

        # Count total
        count_query = select(func.count()).select_from(Task).where(and_(*conditions))
        total = (await db.execute(count_query)).scalar()

        # Fetch tasks
        query = (
            select(Task)
            .where(and_(*conditions))
            .order_by(Task.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        tasks = (await db.execute(query)).scalars().all()

        logger.info(
            "Retrieved project tasks",
            project_id=project_id,
            total=total,
            returned=len(tasks),
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
        logger.exception(
            "Error getting project tasks", project_id=project_id, error=str(e)
        )
        raise HTTPException(500, "Internal server error")
