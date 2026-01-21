import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, func, and_
from sqlalchemy.exc import SQLAlchemyError
from app.core.db import get_db
from app.core.logging import get_logger
from app.core.enums import MessageRole
from app.schemas.chat import ChatPostIn
from app.models.message import Message
from app.workers.tasks import extract_and_store_draft

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = get_logger(__name__)


@router.get("/messages", response_model=dict)
async def get_messages(
    role: Optional[str] = Query(None, description="Filter by role (user/assistant/system)"),
    limit: int = Query(50, ge=1, le=200, description="Max number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get chat message history with optional filtering and pagination.

    Messages are returned in reverse chronological order (newest first).

    Filters:
    - role: user, assistant, or system

    Returns paginated message list with total count.
    """
    try:
        # Build query with filters
        conditions = []

        if role:
            try:
                MessageRole(role)  # Validate
                conditions.append(Message.role == role)
            except ValueError:
                raise HTTPException(400, f"Invalid role: {role}")

        # Count total matching messages
        count_query = select(func.count()).select_from(Message)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = (await db.execute(count_query)).scalar()

        # Fetch messages with pagination (newest first)
        query = select(Message)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(Message.created_at.desc()).limit(limit).offset(offset)

        messages = (await db.execute(query)).scalars().all()

        logger.info(
            "Retrieved messages",
            total=total,
            returned=len(messages),
            role=role,
        )

        return {
            "messages": [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "event_id": str(m.event_id) if m.event_id else None,
                    "created_at": m.created_at,
                }
                for m in messages
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error retrieving messages", error=str(e))
        raise HTTPException(500, "Internal server error")


@router.get("/messages/{message_id}")
async def get_message(message_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single message by ID"""
    try:
        message_uuid = uuid.UUID(message_id)
    except ValueError:
        raise HTTPException(400, "Invalid message_id format")

    try:
        message = (
            await db.execute(select(Message).where(Message.id == message_uuid))
        ).scalars().first()

        if not message:
            logger.warning("Message not found", message_id=message_id)
            raise HTTPException(404, "Message not found")

        logger.debug("Retrieved message", message_id=message_id)
        return {
            "id": str(message.id),
            "role": message.role,
            "content": message.content,
            "event_id": str(message.event_id) if message.event_id else None,
            "created_at": message.created_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error retrieving message", message_id=message_id, error=str(e))
        raise HTTPException(500, "Internal server error")


@router.post("/messages", status_code=201)
async def post_message(payload: ChatPostIn, db: AsyncSession = Depends(get_db)):
    """
    Post a new user message to the chat.

    This will:
    1. Store the message in the database
    2. Queue a background task to extract tasks using LLM
    3. Return immediately with message ID and queued status

    The extracted task drafts can be retrieved via GET /api/task-drafts
    """
    try:
        logger.info("Posting chat message", content_length=len(payload.content))

        # Validate content is not empty
        if not payload.content.strip():
            raise HTTPException(400, "Message content cannot be empty")

        # Store message
        res = await db.execute(
            insert(Message)
            .values(role=MessageRole.USER.value, content=payload.content)
            .returning(Message.id)
        )
        message_id = res.scalar_one()
        await db.commit()

        logger.info("Message stored", message_id=str(message_id))

        # Queue async task extraction
        try:
            extract_and_store_draft.delay(str(message_id), payload.content)
            logger.info("Task extraction queued", message_id=str(message_id))
        except Exception as e:
            logger.error(
                "Failed to queue task extraction",
                message_id=str(message_id),
                error=str(e),
            )
            # Don't fail the request if queueing fails
            # Message is already stored, user can retry extraction later if needed

        return {
            "message_id": str(message_id),
            "status": "queued",
            "message": "Message received and task extraction queued",
        }

    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Database error posting message", error=str(e))
        raise HTTPException(500, "Database error occurred")
    except Exception as e:
        await db.rollback()
        logger.exception("Unexpected error posting message", error=str(e))
        raise HTTPException(500, f"Unexpected error: {str(e)}")
