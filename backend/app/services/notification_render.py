from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import LLMAPIError, RetryableError
from app.models.notification_event import NotificationEvent
from app.models.notification_delivery import NotificationDelivery
from app.models.message import Message
from app.services.llm import call_llm_json

logger = get_logger(__name__)


def _tz() -> ZoneInfo:
    return ZoneInfo(settings.TZ)


REMINDER_SYSTEM_PROMPT = """
You write a deadline reminder announcement for a personal task manager.
Return ONLY JSON: {"text": "..."}.

Requirements (style A):
- Make it actionable: include a "next step" that can be done in ~15 minutes.
- Ask at most ONE clarification question, only if needed.
- Be concise but specific.
- Use Japanese.
""".strip()

FOLLOWUP_SYSTEM_PROMPT = """
You write a short follow-up summary (morning/noon/evening) for a personal task manager.
Return ONLY JSON: {"text": "..."}.
Use Japanese. Be concise, prioritize urgent items, avoid repetition.
""".strip()


async def _render_event_text(ev: NotificationEvent) -> str:
    """
    Render notification event text using LLM.

    Args:
        ev: NotificationEvent to render

    Returns:
        Rendered text string

    Raises:
        LLMAPIError: When LLM API call fails
        ValueError: When event kind is unknown
    """
    try:
        payload_text = json.dumps(ev.payload, ensure_ascii=False)

        if ev.kind == "task_deadline_reminder":
            logger.debug(
                "Rendering deadline reminder",
                event_id=str(ev.id),
                task_id=str(ev.task_id) if ev.task_id else None
            )
            raw = await call_llm_json(REMINDER_SYSTEM_PROMPT, payload_text)
            text = str(raw.get("text", "")).strip()
            if not text:
                raise ValueError("Empty text in LLM response")
            return text

        if ev.kind == "followup_summary":
            logger.debug(
                "Rendering followup summary",
                event_id=str(ev.id),
                slot=ev.slot
            )
            raw = await call_llm_json(FOLLOWUP_SYSTEM_PROMPT, payload_text)
            text = str(raw.get("text", "")).strip()
            if not text:
                raise ValueError("Empty text in LLM response")
            return text

        raise ValueError(f"Unknown event kind: {ev.kind}")

    except LLMAPIError:
        # Re-raise LLM errors as-is
        raise
    except Exception as e:
        logger.error(
            "Error rendering event text",
            event_id=str(ev.id),
            kind=ev.kind,
            error=str(e)
        )
        raise


async def render_and_project_in_app(db: AsyncSession, batch_size: int | None = None) -> int:
    """
    Render NotificationEvents with status='created' and project them to in-app channels.

    Creates notification_deliveries (in_app) and messages (assistant with event_id).
    Each event is processed in its own transaction for better error isolation.

    Args:
        db: Database session
        batch_size: Maximum number of events to process in one call

    Returns:
        Number of successfully processed events
    """
    if batch_size is None:
        batch_size = settings.RENDER_BATCH_SIZE

    try:
        events = (
            await db.execute(
                select(NotificationEvent)
                .where(NotificationEvent.status == "created")
                .order_by(NotificationEvent.created_at.asc())
                .limit(batch_size)
            )
        ).scalars().all()

        logger.info(
            "Starting notification rendering batch",
            batch_size=len(events)
        )

    except SQLAlchemyError as e:
        logger.error(
            "Database error fetching events to render",
            error=str(e)
        )
        raise

    processed = 0
    failed = 0
    now = datetime.now(tz=_tz())

    for ev in events:
        # Process each event individually with savepoint
        try:
            async with db.begin_nested():  # Savepoint for transaction isolation
                logger.info(
                    "Processing notification event",
                    event_id=str(ev.id),
                    kind=ev.kind
                )

                text = await _render_event_text(ev)
                if not text:
                    raise ValueError("Empty rendered text")

                # Update event status
                await db.execute(
                    update(NotificationEvent)
                    .where(NotificationEvent.id == ev.id)
                    .values(status="rendered", rendered_text=text, rendered_at=now)
                )

                # Create delivery record (Phase1: in_app only)
                await db.execute(
                    insert(NotificationDelivery).values(
                        event_id=ev.id,
                        channel="in_app",
                        status="sent",
                        sent_at=now,
                    )
                )

                # Project to messages table
                await db.execute(
                    insert(Message).values(
                        role="assistant",
                        content=text,
                        event_id=ev.id,
                    )
                )

                processed += 1
                logger.info(
                    "Successfully rendered notification",
                    event_id=str(ev.id)
                )

        except LLMAPIError as e:
            failed += 1
            error_msg = f"LLM error: {e.message}"
            logger.error(
                "LLM API error rendering notification",
                event_id=str(ev.id),
                error=error_msg,
                details=e.details
            )
            # Mark as failed with error details
            await db.execute(
                update(NotificationEvent)
                .where(NotificationEvent.id == ev.id)
                .values(status="failed", rendered_text=error_msg)
            )

        except SQLAlchemyError as e:
            failed += 1
            error_msg = f"Database error: {str(e)}"
            logger.error(
                "Database error rendering notification",
                event_id=str(ev.id),
                error=error_msg
            )
            # Try to mark as failed (might fail if DB issue persists)
            try:
                await db.execute(
                    update(NotificationEvent)
                    .where(NotificationEvent.id == ev.id)
                    .values(status="failed", rendered_text=error_msg[:500])
                )
            except Exception:
                logger.exception("Failed to update event status after error")

        except Exception as e:
            failed += 1
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(
                "Unexpected error rendering notification",
                event_id=str(ev.id),
                error=error_msg
            )
            # Mark as failed
            try:
                await db.execute(
                    update(NotificationEvent)
                    .where(NotificationEvent.id == ev.id)
                    .values(status="failed", rendered_text=error_msg[:500])
                )
            except Exception:
                logger.exception("Failed to update event status after error")

    # Commit all changes
    try:
        await db.commit()
        logger.info(
            "Notification rendering batch completed",
            processed=processed,
            failed=failed,
            total=len(events)
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            "Failed to commit notification rendering batch",
            error=str(e)
        )
        raise

    return processed
