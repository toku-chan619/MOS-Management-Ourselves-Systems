"""
Webhook endpoints for receiving messages from external services.
"""
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
import hmac
import hashlib
import base64

from app.core.config import settings
from app.core.logging import logger
from app.services.chat import process_user_message_async
from app.services.notifications import send_draft_notification

router = APIRouter(prefix="/webhook", tags=["webhook"])


def verify_line_signature(body: bytes, signature: str) -> bool:
    """Verify LINE webhook signature."""
    if not settings.LINE_CHANNEL_SECRET:
        logger.warning("LINE_CHANNEL_SECRET not configured, skipping verification")
        return True

    hash_digest = hmac.new(
        settings.LINE_CHANNEL_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(hash_digest).decode('utf-8')

    return hmac.compare_digest(signature, expected_signature)


def verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    """Verify Slack webhook signature."""
    if not settings.SLACK_SIGNING_SECRET:
        logger.warning("SLACK_SIGNING_SECRET not configured, skipping verification")
        return True

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected_signature = 'v0=' + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode('utf-8'),
        sig_basestring.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


@router.post("/line")
async def line_webhook(
    request: Request,
    x_line_signature: Optional[str] = Header(None)
):
    """
    LINE Messaging API Webhook endpoint.

    Receives messages from LINE and processes them as task inputs.
    """
    body = await request.body()

    # Verify signature
    if x_line_signature:
        if not verify_line_signature(body, x_line_signature):
            logger.warning("Invalid LINE signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = await request.json()
        events = payload.get("events", [])

        for event in events:
            if event.get("type") == "message" and event.get("message", {}).get("type") == "text":
                user_message = event["message"]["text"]
                user_id = event["source"].get("userId", "unknown")

                logger.info(f"Received LINE message from {user_id}: {user_message}")

                # Process message asynchronously
                # Note: In production, you might want to queue this
                result = await process_user_message_async(user_message)

                if result and result.get("drafts"):
                    draft_count = len(result["drafts"])
                    await send_draft_notification(draft_count)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error processing LINE webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/slack")
async def slack_webhook(
    request: Request,
    x_slack_request_timestamp: Optional[str] = Header(None),
    x_slack_signature: Optional[str] = Header(None)
):
    """
    Slack Events API Webhook endpoint.

    Receives messages from Slack and processes them as task inputs.
    """
    body = await request.body()

    # Verify signature
    if x_slack_signature and x_slack_request_timestamp:
        if not verify_slack_signature(body, x_slack_request_timestamp, x_slack_signature):
            logger.warning("Invalid Slack signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = await request.json()

        # Handle URL verification challenge
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}

        # Handle event
        if payload.get("type") == "event_callback":
            event = payload.get("event", {})

            # Ignore bot messages to prevent loops
            if event.get("bot_id"):
                return {"status": "ok"}

            if event.get("type") == "message" and event.get("text"):
                user_message = event["text"]
                user_id = event.get("user", "unknown")

                logger.info(f"Received Slack message from {user_id}: {user_message}")

                # Process message
                result = await process_user_message_async(user_message)

                if result and result.get("drafts"):
                    draft_count = len(result["drafts"])
                    await send_draft_notification(draft_count)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error processing Slack webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discord")
async def discord_webhook(request: Request):
    """
    Discord Webhook endpoint.

    Note: Discord webhooks are outgoing only by default.
    This endpoint can be used with Discord bot integration for receiving messages.
    """
    try:
        payload = await request.json()

        # Discord bot message format
        if payload.get("type") == 0:  # MESSAGE_CREATE
            content = payload.get("content", "")
            author_id = payload.get("author", {}).get("id")

            # Ignore bot messages
            if payload.get("author", {}).get("bot"):
                return {"status": "ok"}

            logger.info(f"Received Discord message from {author_id}: {content}")

            # Process message
            result = await process_user_message_async(content)

            if result and result.get("drafts"):
                draft_count = len(result["drafts"])
                await send_draft_notification(draft_count)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error processing Discord webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def webhook_status():
    """Get webhook configuration status."""
    from app.services.notifications import notification_manager

    return {
        "configured_providers": notification_manager.get_configured_providers(),
        "line_webhook_enabled": bool(settings.LINE_CHANNEL_SECRET),
        "slack_webhook_enabled": bool(settings.SLACK_SIGNING_SECRET),
    }
