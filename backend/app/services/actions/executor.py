"""
Action execution engine.

Manages the lifecycle of task actions: propose → approve → execute → complete.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_action import TaskAction, ActionStatus, ActionType
from app.models.task import Task
from app.services.actions.registry import action_registry
from app.services.actions.base import ActionResult
from app.core.logging import logger


class ActionExecutionEngine:
    """Engine for executing task actions with full lifecycle management."""

    async def create_proposed_action(
        self,
        db: AsyncSession,
        task_id: UUID,
        action_type: str,
        parameters: Dict[str, Any],
        reasoning: str,
        confidence: float = 0.5
    ) -> TaskAction:
        """
        Create a new proposed action for a task.

        Args:
            db: Database session
            task_id: Task ID
            action_type: Type of action
            parameters: Action parameters
            reasoning: Why this action is suggested
            confidence: Confidence score (0.0-1.0)

        Returns:
            Created TaskAction object
        """
        try:
            # Validate action type exists
            if not action_registry.has_action(action_type):
                raise ValueError(f"Unknown action type: {action_type}")

            # Create action record
            action = TaskAction(
                action_id=uuid4(),
                task_id=task_id,
                action_type=ActionType(action_type),
                status=ActionStatus.PROPOSED,
                parameters=parameters,
                reasoning=reasoning,
                confidence=confidence,
                created_at=datetime.utcnow()
            )

            db.add(action)
            await db.commit()
            await db.refresh(action)

            logger.info(
                "Proposed action created",
                action_id=str(action.action_id),
                task_id=task_id,
                action_type=action_type
            )

            return action

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to create proposed action",
                task_id=task_id,
                action_type=action_type,
                error=str(e)
            )
            raise

    async def approve_action(
        self,
        db: AsyncSession,
        action_id: UUID,
        user_id: Optional[int] = None
    ) -> TaskAction:
        """
        Approve a proposed action.

        Args:
            db: Database session
            action_id: Action ID
            user_id: Optional user ID who approved

        Returns:
            Updated TaskAction
        """
        try:
            # Get action
            result = await db.execute(
                select(TaskAction).where(TaskAction.action_id == action_id)
            )
            action = result.scalar_one_or_none()

            if not action:
                raise ValueError(f"Action not found: {action_id}")

            if action.status != ActionStatus.PROPOSED:
                raise ValueError(
                    f"Action must be in PROPOSED status, got: {action.status}"
                )

            # Update status
            action.status = ActionStatus.APPROVED
            action.approved_at = datetime.utcnow()
            if user_id:
                action.approved_by = user_id

            await db.commit()
            await db.refresh(action)

            logger.info(
                "Action approved",
                action_id=str(action_id),
                task_id=action.task_id
            )

            return action

        except Exception as e:
            await db.rollback()
            logger.error("Failed to approve action", action_id=str(action_id), error=str(e))
            raise

    async def execute_action(
        self,
        db: AsyncSession,
        action_id: UUID,
        dry_run: bool = False
    ) -> ActionResult:
        """
        Execute an approved action.

        Args:
            db: Database session
            action_id: Action ID
            dry_run: If True, simulate execution without making changes

        Returns:
            ActionResult with execution outcome
        """
        try:
            # Get action
            result = await db.execute(
                select(TaskAction).where(TaskAction.action_id == action_id)
            )
            action = result.scalar_one_or_none()

            if not action:
                raise ValueError(f"Action not found: {action_id}")

            if action.status not in [ActionStatus.APPROVED, ActionStatus.FAILED]:
                raise ValueError(
                    f"Action must be APPROVED or FAILED (for retry), got: {action.status}"
                )

            # Update status to EXECUTING
            action.status = ActionStatus.EXECUTING
            action.executed_at = datetime.utcnow()
            await db.commit()

            logger.info(
                "Executing action",
                action_id=str(action_id),
                action_type=action.action_type.value,
                dry_run=dry_run
            )

            # Get executor
            executor_class = action_registry.get_executor(action.action_type.value)
            executor = executor_class(action.parameters)

            # Execute or dry run
            if dry_run:
                result = await executor.dry_run()
            else:
                result = await executor.execute()

            # Update action based on result
            if result.success:
                action.status = ActionStatus.COMPLETED
                action.result = result.data or {}
                action.completed_at = datetime.utcnow()

                logger.info(
                    "Action completed successfully",
                    action_id=str(action_id)
                )
            else:
                action.status = ActionStatus.FAILED
                action.result = {"error": result.error}

                logger.error(
                    "Action execution failed",
                    action_id=str(action_id),
                    error=result.error
                )

            await db.commit()
            await db.refresh(action)

            return result

        except Exception as e:
            # Mark action as failed
            try:
                action.status = ActionStatus.FAILED
                action.result = {"error": str(e)}
                await db.commit()
            except Exception:
                await db.rollback()

            logger.exception(
                "Error executing action",
                action_id=str(action_id),
                error=str(e)
            )

            return ActionResult(
                success=False,
                error=str(e)
            )

    async def cancel_action(
        self,
        db: AsyncSession,
        action_id: UUID
    ) -> TaskAction:
        """
        Cancel a proposed or approved action.

        Args:
            db: Database session
            action_id: Action ID

        Returns:
            Updated TaskAction
        """
        try:
            result = await db.execute(
                select(TaskAction).where(TaskAction.action_id == action_id)
            )
            action = result.scalar_one_or_none()

            if not action:
                raise ValueError(f"Action not found: {action_id}")

            if action.status not in [ActionStatus.PROPOSED, ActionStatus.APPROVED]:
                raise ValueError(
                    f"Can only cancel PROPOSED or APPROVED actions, got: {action.status}"
                )

            action.status = ActionStatus.CANCELLED
            action.completed_at = datetime.utcnow()

            await db.commit()
            await db.refresh(action)

            logger.info(
                "Action cancelled",
                action_id=str(action_id)
            )

            return action

        except Exception as e:
            await db.rollback()
            logger.error("Failed to cancel action", action_id=str(action_id), error=str(e))
            raise

    async def rollback_action(
        self,
        db: AsyncSession,
        action_id: UUID
    ) -> ActionResult:
        """
        Attempt to rollback a completed action.

        Args:
            db: Database session
            action_id: Action ID

        Returns:
            ActionResult with rollback outcome
        """
        try:
            result = await db.execute(
                select(TaskAction).where(TaskAction.action_id == action_id)
            )
            action = result.scalar_one_or_none()

            if not action:
                raise ValueError(f"Action not found: {action_id}")

            if action.status != ActionStatus.COMPLETED:
                raise ValueError(
                    f"Can only rollback COMPLETED actions, got: {action.status}"
                )

            # Get executor
            executor_class = action_registry.get_executor(action.action_type.value)
            executor = executor_class(action.parameters)

            # Check if rollback is supported
            if not executor.can_rollback():
                return ActionResult(
                    success=False,
                    error="This action type does not support rollback"
                )

            logger.info(
                "Rolling back action",
                action_id=str(action_id),
                action_type=action.action_type.value
            )

            # Perform rollback
            rollback_result = await executor.rollback(action.result or {})

            if rollback_result.success:
                # Update action to show it was rolled back
                action.result = action.result or {}
                action.result["rolled_back"] = True
                action.result["rollback_at"] = datetime.utcnow().isoformat()
                await db.commit()

                logger.info(
                    "Action rolled back successfully",
                    action_id=str(action_id)
                )
            else:
                logger.error(
                    "Action rollback failed",
                    action_id=str(action_id),
                    error=rollback_result.error
                )

            return rollback_result

        except Exception as e:
            await db.rollback()
            logger.exception("Error rolling back action", action_id=str(action_id), error=str(e))
            return ActionResult(
                success=False,
                error=str(e)
            )

    async def get_task_actions(
        self,
        db: AsyncSession,
        task_id: UUID,
        status: Optional[ActionStatus] = None
    ) -> List[TaskAction]:
        """
        Get all actions for a task.

        Args:
            db: Database session
            task_id: Task ID
            status: Optional status filter

        Returns:
            List of TaskAction objects
        """
        query = select(TaskAction).where(TaskAction.task_id == task_id)

        if status:
            query = query.where(TaskAction.status == status)

        query = query.order_by(TaskAction.created_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_action(
        self,
        db: AsyncSession,
        action_id: UUID
    ) -> Optional[TaskAction]:
        """
        Get a specific action by ID.

        Args:
            db: Database session
            action_id: Action ID

        Returns:
            TaskAction or None
        """
        result = await db.execute(
            select(TaskAction).where(TaskAction.action_id == action_id)
        )
        return result.scalar_one_or_none()

    async def execute_all_approved_actions(
        self,
        db: AsyncSession,
        task_id: UUID
    ) -> List[ActionResult]:
        """
        Execute all approved actions for a task.

        Args:
            db: Database session
            task_id: Task ID

        Returns:
            List of ActionResult objects
        """
        # Get all approved actions
        actions = await self.get_task_actions(
            db, task_id, status=ActionStatus.APPROVED
        )

        results = []
        for action in actions:
            result = await self.execute_action(db, action.action_id)
            results.append(result)

        return results


# Global instance
execution_engine = ActionExecutionEngine()
