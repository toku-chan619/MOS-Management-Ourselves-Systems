from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from sqlalchemy.exc import SQLAlchemyError
from app.core.db import get_db
from app.core.logging import get_logger
from app.core.enums import FollowupSlot
from app.models.message import Message
from app.models.followup_run import FollowupRun
from app.services.followup import build_followup_text

router = APIRouter(prefix="/api/followup", tags=["followup"])
logger = get_logger(__name__)


@router.post("/run")
async def run_followup(slot: str, db: AsyncSession = Depends(get_db)):
    """
    Run a followup for the specified time slot.

    This endpoint:
    1. Validates the slot parameter
    2. Builds followup text using LLM
    3. Records the followup run
    4. Creates a message for display

    All operations are performed in a single transaction.

    Args:
        slot: Time slot (morning, noon, or evening)
        db: Database session

    Returns:
        Success response with slot name
    """
    # Validate slot
    try:
        slot_enum = FollowupSlot(slot)
    except ValueError:
        valid_slots = [s.value for s in FollowupSlot]
        logger.warning(
            "Invalid followup slot",
            slot=slot,
            valid_slots=valid_slots
        )
        raise HTTPException(
            400,
            f"Invalid slot. Must be one of: {', '.join(valid_slots)}"
        )

    logger.info("Starting followup run", slot=slot)

    try:
        # Use transaction for atomicity
        async with db.begin_nested():
            # Build followup text
            text = await build_followup_text(db, slot)

            if not text:
                logger.warning("Empty followup text generated", slot=slot)
                raise HTTPException(500, "Failed to generate followup text")

            # Record followup run
            await db.execute(
                insert(FollowupRun).values(slot=slot)
            )

            # Create message
            await db.execute(
                insert(Message).values(
                    role="assistant",
                    content=text
                )
            )

        await db.commit()

        logger.info(
            "Followup run completed successfully",
            slot=slot,
            text_length=len(text)
        )

        return {"ok": True, "slot": slot, "message": text}

    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            "Database error during followup run",
            slot=slot,
            error=str(e)
        )
        raise HTTPException(500, "Database error occurred")

    except Exception as e:
        await db.rollback()
        logger.exception(
            "Unexpected error during followup run",
            slot=slot,
            error=str(e)
        )
        raise HTTPException(500, f"Unexpected error: {str(e)}")
