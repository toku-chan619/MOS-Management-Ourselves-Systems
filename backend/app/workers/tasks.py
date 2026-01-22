import asyncio
from celery import Task
from sqlalchemy import insert
from sqlalchemy.exc import SQLAlchemyError
from app.workers.celery_app import celery_app
from app.core.db import SessionLocal
from app.services.extraction import extract_draft
from app.models.draft import TaskDraft
from app.models.agent_run import AgentRun
from app.core.config import settings
from app.core.exceptions import LLMAPIError, RetryableError, DatabaseError
from app.core.logging import get_logger

logger = get_logger(__name__)


class CallbackTask(Task):
    """Base task with error handling callbacks"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        logger.error(
            "Task failed",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            args=args,
            kwargs=kwargs
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        logger.warning(
            "Task retrying",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            args=args
        )

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        logger.info(
            "Task completed successfully",
            task_id=task_id,
            task_name=self.name
        )


@celery_app.task(
    name="mos.extract_and_store_draft",
    base=CallbackTask,
    bind=True,
    autoretry_for=(RetryableError, SQLAlchemyError),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def extract_and_store_draft(self, message_id: str, user_text: str):
    """
    Extract task draft from user text using LLM and store in database.

    This task includes automatic retry logic for transient failures.
    """

    async def _run():
        try:
            logger.info(
                "Starting task extraction",
                message_id=message_id,
                text_length=len(user_text)
            )

            # Extract draft using LLM
            draft = await extract_draft(user_text)
            overall_conf = 0.0
            if draft.tasks:
                overall_conf = sum(t.confidence for t in draft.tasks) / len(draft.tasks)

            logger.info(
                "Draft extracted successfully",
                message_id=message_id,
                num_tasks=len(draft.tasks) if draft.tasks else 0,
                confidence=overall_conf
            )

            # Store in database
            async with SessionLocal() as db:
                try:
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

                    logger.info(
                        "Draft stored successfully",
                        message_id=message_id
                    )

                    # Send notification if drafts were created
                    if draft.tasks and len(draft.tasks) > 0:
                        try:
                            from app.services.notifications import send_draft_notification
                            await send_draft_notification(len(draft.tasks))
                            logger.info("Draft notification sent", count=len(draft.tasks))
                        except Exception as e:
                            logger.error("Failed to send draft notification", error=str(e))

                except SQLAlchemyError as e:
                    await db.rollback()
                    logger.error(
                        "Database error storing draft",
                        message_id=message_id,
                        error=str(e)
                    )
                    raise DatabaseError(
                        "Failed to store draft in database",
                        {"message_id": message_id, "error": str(e)}
                    )

        except LLMAPIError as e:
            logger.error(
                "LLM API error",
                message_id=message_id,
                error=str(e),
                details=e.details
            )
            # Don't retry on permanent LLM errors
            raise

        except RetryableError as e:
            logger.warning(
                "Retryable error occurred",
                message_id=message_id,
                error=str(e)
            )
            # Will be automatically retried by Celery
            raise

        except Exception as e:
            logger.exception(
                "Unexpected error in task extraction",
                message_id=message_id,
                error=str(e)
            )
            raise

    try:
        asyncio.run(_run())
    except Exception as e:
        logger.exception(
            "Task execution failed",
            message_id=message_id,
            error=str(e)
        )
        raise
