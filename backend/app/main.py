from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.logging import get_logger
from app.core.exceptions import MOSException

from app.routers.chat import router as chat_router
from app.routers.drafts import router as drafts_router
from app.routers.tasks import router as tasks_router
from app.routers.projects import router as projects_router
from app.routers.followup import router as followup_router
from app.routers.webhook import router as webhook_router

from app.routers.reminders import router as reminders_router
from app.routers.notifications import router as notifications_router
from app.routers.actions import router as actions_router

from app.services.reminders import scan_deadline_reminders
from app.services.notification_render import render_and_project_in_app
from app.services.followup import build_followup_text
from app.models.followup_run import FollowupRun
from sqlalchemy import insert

# Messaging Integration
from app.services.messaging.manager import MessagingManager
from app.services.messaging.telegram import TelegramChannel
from app.services.messaging.slack import SlackChannel
from app.services.messaging.integration import MessagingIntegration

logger = get_logger(__name__)

# Global messaging manager
messaging_manager: MessagingManager = None
messaging_integration: MessagingIntegration = None

app = FastAPI(
    title="MOS Backend",
    description="Management Ourselves System - Personal Task Management with AI",
    version="0.1.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(MOSException)
async def mos_exception_handler(request: Request, exc: MOSException):
    """Handle custom MOS exceptions"""
    logger.error(
        "MOS exception occurred",
        path=request.url.path,
        error=exc.message,
        details=exc.details
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": exc.message,
            "details": exc.details,
        },
    )

app.include_router(chat_router)
app.include_router(drafts_router)
app.include_router(tasks_router)
app.include_router(projects_router)
app.include_router(followup_router)
app.include_router(webhook_router)

app.include_router(reminders_router)
app.include_router(notifications_router)
app.include_router(actions_router)

scheduler = AsyncIOScheduler(timezone=ZoneInfo(settings.TZ))


@app.on_event("startup")
async def startup():
    """Application startup: Initialize scheduler and background jobs"""
    global messaging_manager, messaging_integration

    logger.info(
        "Starting MOS Backend",
        version="0.1.0",
        timezone=settings.TZ,
        reminder_interval_min=settings.REMINDER_SCAN_INTERVAL_MIN
    )

    # Initialize messaging system
    messaging_manager = MessagingManager()

    # Setup Telegram Bot if configured
    if settings.TELEGRAM_BOT_TOKEN:
        logger.info("Initializing Telegram Bot integration")
        telegram = TelegramChannel(
            token=settings.TELEGRAM_BOT_TOKEN,
            allowed_users=settings.telegram_allowed_users_list,
        )

        # Create integration service
        async with SessionLocal() as db:
            messaging_integration = MessagingIntegration(messaging_manager, db)

            # Register handlers
            telegram.on_message(messaging_integration.handle_incoming_message)
            telegram.on_button_click("*", messaging_integration.handle_button_click)

        messaging_manager.register_channel(telegram)
    else:
        logger.info("Telegram Bot not configured")

    # Setup Slack Bot if configured
    if settings.SLACK_BOT_TOKEN:
        logger.info("Initializing Slack Bot integration")
        slack = SlackChannel(
            bot_token=settings.SLACK_BOT_TOKEN,
            app_token=settings.SLACK_APP_TOKEN if settings.SLACK_APP_TOKEN else None,
        )

        # Create integration service if not already created
        if not messaging_integration:
            async with SessionLocal() as db:
                messaging_integration = MessagingIntegration(messaging_manager, db)

        # Register handlers
        slack.on_message(messaging_integration.handle_incoming_message)
        slack.on_button_click("*", messaging_integration.handle_button_click)

        messaging_manager.register_channel(slack)
    else:
        logger.info("Slack Bot not configured")

    # Start all messaging channels
    if messaging_manager.list_channels():
        await messaging_manager.start_all()
        logger.info("Messaging system initialized", channels=messaging_manager.list_channels())
    else:
        logger.info("No messaging channels configured")

    async def scan_job():
        """Scan for deadline reminders"""
        try:
            async with SessionLocal() as db:
                count = await scan_deadline_reminders(db, limit_new_events=10)
                if count > 0:
                    logger.info("Deadline scan completed", events_created=count)
        except Exception as e:
            logger.exception("Error in deadline scan job", error=str(e))

    async def render_job():
        """Render pending notifications"""
        try:
            async with SessionLocal() as db:
                count = await render_and_project_in_app(db)
                if count > 0:
                    logger.info("Notification render completed", notifications_rendered=count)
        except Exception as e:
            logger.exception("Error in notification render job", error=str(e))

    async def followup_job(slot: str):
        """Run followup for specific time slot"""
        try:
            async with SessionLocal() as db:
                text = await build_followup_text(db, slot)
                if text:
                    from app.models.message import Message
                    from app.services.notifications import send_followup_notification

                    await db.execute(insert(FollowupRun).values(slot=slot))
                    await db.execute(
                        insert(Message).values(role="assistant", content=text)
                    )
                    await db.commit()
                    logger.info("Followup completed", slot=slot, text_length=len(text))

                    # Send external notifications
                    try:
                        results = await send_followup_notification(slot, text)
                        logger.info("Followup notifications sent", results=results)
                    except Exception as e:
                        logger.error("Failed to send followup notifications", error=str(e))
                else:
                    logger.warning("Empty followup text generated", slot=slot)
        except Exception as e:
            logger.exception("Error in followup job", slot=slot, error=str(e))

    # Schedule deadline scanning
    scheduler.add_job(
        scan_job,
        IntervalTrigger(minutes=settings.REMINDER_SCAN_INTERVAL_MIN),
        id="deadline_scan",
        max_instances=1,
        coalesce=True,
    )
    logger.info(
        "Scheduled deadline scan job",
        interval_minutes=settings.REMINDER_SCAN_INTERVAL_MIN
    )

    # Schedule notification rendering (Phase1 simple worker)
    scheduler.add_job(
        render_job,
        IntervalTrigger(minutes=1),
        id="notification_render",
        max_instances=1,
        coalesce=True,
    )
    logger.info("Scheduled notification render job", interval_minutes=1)

    # Schedule followups at specific times
    # Parse time strings (format: "HH:MM")
    def parse_time(time_str: str) -> tuple[int, int]:
        """Parse time string 'HH:MM' into (hour, minute)"""
        parts = time_str.split(":")
        return int(parts[0]), int(parts[1])

    morning_hour, morning_minute = parse_time(settings.FOLLOWUP_MORNING)
    noon_hour, noon_minute = parse_time(settings.FOLLOWUP_NOON)
    evening_hour, evening_minute = parse_time(settings.FOLLOWUP_EVENING)

    # Morning followup
    scheduler.add_job(
        lambda: followup_job("morning"),
        CronTrigger(hour=morning_hour, minute=morning_minute, timezone=settings.TZ),
        id="followup_morning",
        max_instances=1,
        coalesce=True,
    )
    logger.info(
        "Scheduled morning followup",
        time=settings.FOLLOWUP_MORNING,
        timezone=settings.TZ,
    )

    # Noon followup
    scheduler.add_job(
        lambda: followup_job("noon"),
        CronTrigger(hour=noon_hour, minute=noon_minute, timezone=settings.TZ),
        id="followup_noon",
        max_instances=1,
        coalesce=True,
    )
    logger.info(
        "Scheduled noon followup",
        time=settings.FOLLOWUP_NOON,
        timezone=settings.TZ,
    )

    # Evening followup
    scheduler.add_job(
        lambda: followup_job("evening"),
        CronTrigger(hour=evening_hour, minute=evening_minute, timezone=settings.TZ),
        id="followup_evening",
        max_instances=1,
        coalesce=True,
    )
    logger.info(
        "Scheduled evening followup",
        time=settings.FOLLOWUP_EVENING,
        timezone=settings.TZ,
    )

    scheduler.start()
    logger.info("Scheduler started successfully")


@app.on_event("shutdown")
async def shutdown():
    """Application shutdown: Clean up resources"""
    global messaging_manager

    logger.info("Shutting down MOS Backend")

    # Stop messaging system
    if messaging_manager:
        await messaging_manager.stop_all()
        logger.info("Messaging system stopped")

    scheduler.shutdown()
    logger.info("Scheduler stopped")
