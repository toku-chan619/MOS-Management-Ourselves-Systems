"""
External notification services for sending updates to LINE, Slack, Discord, etc.
"""
import httpx
import hmac
import hashlib
from typing import Optional, Dict, Any
from enum import Enum

from app.core.config import settings
from app.core.logging import logger


class NotificationProvider(str, Enum):
    """Supported notification providers."""
    LINE_NOTIFY = "line_notify"
    SLACK = "slack"
    DISCORD = "discord"


class NotificationService:
    """Base notification service."""

    async def send_message(self, message: str) -> bool:
        """Send a message. Returns True if successful."""
        raise NotImplementedError


class LineNotifyService(NotificationService):
    """LINE Notify service for sending notifications."""

    API_URL = "https://notify-api.line.me/api/notify"

    def __init__(self, token: str):
        self.token = token

    async def send_message(self, message: str) -> bool:
        """Send a message via LINE Notify."""
        if not self.token:
            logger.warning("LINE Notify token not configured")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.API_URL,
                    headers={"Authorization": f"Bearer {self.token}"},
                    data={"message": message},
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info("LINE Notify message sent successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to send LINE Notify: {e}")
            return False


class SlackService(NotificationService):
    """Slack Incoming Webhooks service."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send_message(self, message: str, blocks: Optional[list] = None) -> bool:
        """Send a message via Slack Incoming Webhook."""
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

        try:
            payload = {"text": message}
            if blocks:
                payload["blocks"] = blocks

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info("Slack message sent successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False


class DiscordService(NotificationService):
    """Discord Webhook service."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send_message(
        self,
        message: str,
        embeds: Optional[list] = None,
        username: Optional[str] = "MOS Bot"
    ) -> bool:
        """Send a message via Discord Webhook."""
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured")
            return False

        try:
            payload = {
                "content": message,
                "username": username
            }
            if embeds:
                payload["embeds"] = embeds

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info("Discord message sent successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")
            return False


class NotificationManager:
    """Manages multiple notification providers."""

    def __init__(self):
        self.providers: Dict[NotificationProvider, NotificationService] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize configured providers."""
        # LINE Notify
        if settings.LINE_NOTIFY_TOKEN:
            self.providers[NotificationProvider.LINE_NOTIFY] = LineNotifyService(
                settings.LINE_NOTIFY_TOKEN
            )

        # Slack
        if settings.SLACK_WEBHOOK_URL:
            self.providers[NotificationProvider.SLACK] = SlackService(
                settings.SLACK_WEBHOOK_URL
            )

        # Discord
        if settings.DISCORD_WEBHOOK_URL:
            self.providers[NotificationProvider.DISCORD] = DiscordService(
                settings.DISCORD_WEBHOOK_URL
            )

    async def send_to_all(self, message: str) -> Dict[str, bool]:
        """Send message to all configured providers."""
        results = {}
        for provider, service in self.providers.items():
            results[provider.value] = await service.send_message(message)
        return results

    async def send_to_provider(
        self,
        provider: NotificationProvider,
        message: str
    ) -> bool:
        """Send message to specific provider."""
        service = self.providers.get(provider)
        if not service:
            logger.warning(f"Provider {provider} not configured")
            return False
        return await service.send_message(message)

    def is_configured(self, provider: NotificationProvider) -> bool:
        """Check if a provider is configured."""
        return provider in self.providers

    def get_configured_providers(self) -> list[str]:
        """Get list of configured provider names."""
        return [p.value for p in self.providers.keys()]


# Singleton instance
notification_manager = NotificationManager()


# Helper functions
async def send_followup_notification(period: str, summary: str) -> Dict[str, bool]:
    """Send followup notification to all configured providers."""
    period_emoji = {
        "morning": "☀️",
        "noon": "🌅",
        "evening": "🌙"
    }
    emoji = period_emoji.get(period, "📋")

    message = f"{emoji} {period}のフォローアップ\n\n{summary}"
    return await notification_manager.send_to_all(message)


async def send_draft_notification(draft_count: int) -> Dict[str, bool]:
    """Send notification when drafts are created."""
    message = f"📝 {draft_count}件の新しいタスク案が生成されました\n\nDraftページで確認してください。"
    return await notification_manager.send_to_all(message)


async def send_task_reminder(task_title: str, due_date: str) -> Dict[str, bool]:
    """Send task reminder notification."""
    message = f"⏰ タスクリマインダー\n\nタスク: {task_title}\n期限: {due_date}"
    return await notification_manager.send_to_all(message)
