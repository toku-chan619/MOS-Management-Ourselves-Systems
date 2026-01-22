"""
Task action management endpoints.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.task_action import ActionStatus
from app.services.actions.proposal import propose_actions_for_task
from app.services.actions.executor import execution_engine
from app.core.logging import logger


router = APIRouter(prefix="/api", tags=["actions"])


# Request/Response Models

class ProposeActionsRequest(BaseModel):
    """Request to propose actions for a task."""
    task_title: str = Field(..., description="Task title")
    task_description: Optional[str] = Field(None, description="Task description")
    task_metadata: Optional[dict] = Field(None, description="Task metadata")


class ActionProposalResponse(BaseModel):
    """Response with proposed actions."""
    action_type: str
    parameters: dict
    reasoning: str
    confidence: float


class CreateActionRequest(BaseModel):
    """Request to create a proposed action."""
    action_type: str
    parameters: dict
    reasoning: str
    confidence: float = 0.5


class ActionResponse(BaseModel):
    """Response with action details."""
    action_id: str
    task_id: str
    action_type: str
    status: str
    parameters: dict
    reasoning: str
    confidence: float
    result: Optional[dict]
    created_at: str
    approved_at: Optional[str]
    executed_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class ExecuteActionRequest(BaseModel):
    """Request to execute an action."""
    dry_run: bool = Field(False, description="If true, simulate execution")


class ExecuteActionResponse(BaseModel):
    """Response from action execution."""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


# Endpoints

@router.post("/tasks/{task_id}/actions/propose")
async def propose_actions(
    task_id: UUID,
    request: ProposeActionsRequest,
    db: AsyncSession = Depends(get_db)
) -> List[ActionProposalResponse]:
    """
    Propose actions for a task using LLM analysis.

    This endpoint analyzes the task and suggests helpful automated actions
    that could be performed.
    """
    try:
        # Verify task exists
        from app.models.task import Task
        from sqlalchemy import select
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Propose actions using LLM
        proposals = await propose_actions_for_task(
            task_title=request.task_title,
            task_description=request.task_description,
            task_metadata=request.task_metadata
        )

        # Convert to response format
        return [
            ActionProposalResponse(
                action_type=p.action_type,
                parameters=p.parameters,
                reasoning=p.reasoning,
                confidence=p.confidence
            )
            for p in proposals
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error proposing actions: {e}", task_id=task_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/actions", response_model=ActionResponse)
async def create_action(
    task_id: UUID,
    request: CreateActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a proposed action for a task.

    This creates the action in PROPOSED status, waiting for user approval.
    """
    try:
        # Verify task exists
        from app.models.task import Task
        from sqlalchemy import select
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Create action
        action = await execution_engine.create_proposed_action(
            db=db,
            task_id=task_id,
            action_type=request.action_type,
            parameters=request.parameters,
            reasoning=request.reasoning,
            confidence=request.confidence
        )

        return ActionResponse(
            action_id=str(action.action_id),
            task_id=str(action.task_id),
            action_type=action.action_type.value,
            status=action.status.value,
            parameters=action.parameters,
            reasoning=action.reasoning,
            confidence=action.confidence,
            result=action.result,
            created_at=action.created_at.isoformat(),
            approved_at=action.approved_at.isoformat() if action.approved_at else None,
            executed_at=action.executed_at.isoformat() if action.executed_at else None,
            completed_at=action.completed_at.isoformat() if action.completed_at else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating action: {e}", task_id=task_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/actions", response_model=List[ActionResponse])
async def get_task_actions(
    task_id: UUID,
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all actions for a task.

    Optionally filter by status (proposed, approved, executing, completed, failed, cancelled).
    """
    try:
        # Parse status if provided
        status_filter = None
        if status:
            try:
                status_filter = ActionStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}"
                )

        # Get actions
        actions = await execution_engine.get_task_actions(
            db=db,
            task_id=task_id,
            status=status_filter
        )

        return [
            ActionResponse(
                action_id=str(action.action_id),
                task_id=str(action.task_id),
                action_type=action.action_type.value,
                status=action.status.value,
                parameters=action.parameters,
                reasoning=action.reasoning,
                confidence=action.confidence,
                result=action.result,
                created_at=action.created_at.isoformat(),
                approved_at=action.approved_at.isoformat() if action.approved_at else None,
                executed_at=action.executed_at.isoformat() if action.executed_at else None,
                completed_at=action.completed_at.isoformat() if action.completed_at else None,
            )
            for action in actions
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task actions: {e}", task_id=task_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions/{action_id}", response_model=ActionResponse)
async def get_action(
    action_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get details of a specific action."""
    try:
        action = await execution_engine.get_action(db, action_id)

        if not action:
            raise HTTPException(status_code=404, detail="Action not found")

        return ActionResponse(
            action_id=str(action.action_id),
            task_id=str(action.task_id),
            action_type=action.action_type.value,
            status=action.status.value,
            parameters=action.parameters,
            reasoning=action.reasoning,
            confidence=action.confidence,
            result=action.result,
            created_at=action.created_at.isoformat(),
            approved_at=action.approved_at.isoformat() if action.approved_at else None,
            executed_at=action.executed_at.isoformat() if action.executed_at else None,
            completed_at=action.completed_at.isoformat() if action.completed_at else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting action: {e}", action_id=str(action_id))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/{action_id}/approve", response_model=ActionResponse)
async def approve_action(
    action_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Approve a proposed action.

    This changes the action status from PROPOSED to APPROVED,
    making it ready for execution.
    """
    try:
        action = await execution_engine.approve_action(db, action_id)

        return ActionResponse(
            action_id=str(action.action_id),
            task_id=str(action.task_id),
            action_type=action.action_type.value,
            status=action.status.value,
            parameters=action.parameters,
            reasoning=action.reasoning,
            confidence=action.confidence,
            result=action.result,
            created_at=action.created_at.isoformat(),
            approved_at=action.approved_at.isoformat() if action.approved_at else None,
            executed_at=action.executed_at.isoformat() if action.executed_at else None,
            completed_at=action.completed_at.isoformat() if action.completed_at else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving action: {e}", action_id=str(action_id))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/{action_id}/execute", response_model=ExecuteActionResponse)
async def execute_action(
    action_id: UUID,
    request: ExecuteActionRequest = ExecuteActionRequest(),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute an approved action.

    Set dry_run=true to simulate execution without making actual changes.
    """
    try:
        result = await execution_engine.execute_action(
            db=db,
            action_id=action_id,
            dry_run=request.dry_run
        )

        return ExecuteActionResponse(
            success=result.success,
            data=result.data,
            error=result.error
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing action: {e}", action_id=str(action_id))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/{action_id}/cancel", response_model=ActionResponse)
async def cancel_action(
    action_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a proposed or approved action.

    This prevents the action from being executed.
    """
    try:
        action = await execution_engine.cancel_action(db, action_id)

        return ActionResponse(
            action_id=str(action.action_id),
            task_id=str(action.task_id),
            action_type=action.action_type.value,
            status=action.status.value,
            parameters=action.parameters,
            reasoning=action.reasoning,
            confidence=action.confidence,
            result=action.result,
            created_at=action.created_at.isoformat(),
            approved_at=action.approved_at.isoformat() if action.approved_at else None,
            executed_at=action.executed_at.isoformat() if action.executed_at else None,
            completed_at=action.completed_at.isoformat() if action.completed_at else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling action: {e}", action_id=str(action_id))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/{action_id}/rollback", response_model=ExecuteActionResponse)
async def rollback_action(
    action_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Attempt to rollback a completed action.

    Note: Not all actions support rollback.
    """
    try:
        result = await execution_engine.rollback_action(db, action_id)

        return ExecuteActionResponse(
            success=result.success,
            data=result.data,
            error=result.error
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error rolling back action: {e}", action_id=str(action_id))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions/types")
async def get_action_types():
    """
    Get list of available action types.

    Returns information about all registered action types.
    """
    from app.services.actions.registry import action_registry

    action_types = action_registry.list_actions()

    # Build detailed info for each action type
    results = []
    for action_type in action_types:
        executor_class = action_registry.get_executor(action_type)
        results.append({
            "action_type": action_type,
            "description": executor_class.__doc__ or "No description available",
            "supports_rollback": False  # Would need instance to check
        })

    return results
