"""
Slack Bot integration using slack-bolt.

Inspired by molt.bot's Slack implementation (src/slack/bot.ts)
using slack-bolt Python library.
"""
import logging
import asyncio
from typing import Optional, List
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from app.core.logging import get_logger
from .base import MessagingChannel, MessageContext, MessageButton, ButtonStyle


logger = get_logger(__name__)


class SlackChannel(MessagingChannel):
    """
    Slack Bot implementation of MessagingChannel.

    Features inspired by molt.bot:
    - Message handling with context
    - Interactive buttons (Block Kit)
    - Thread support
    - Socket Mode for easy local development
    """

    def __init__(
        self,
        bot_token: str,
        app_token: Optional[str] = None,  # For Socket Mode
    ):
        super().__init__("slack")
        self.bot_token = bot_token
        self.app_token = app_token
        self.app: Optional[AsyncApp] = None
        self.handler: Optional[AsyncSocketModeHandler] = None

    async def send_message(
        self,
        chat_id: str,  # channel_id or user_id
        text: str,
        buttons: Optional[List[MessageButton]] = None,
        reply_to_message_id: Optional[str] = None,
        thread_id: Optional[str] = None,  # thread_ts in Slack
    ) -> str:
        """Send a message to Slack."""
        if not self.app:
            raise RuntimeError("Slack channel not started")

        # Build blocks for rich formatting
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            }
        ]

        # Add buttons as actions block
        if buttons:
            actions = []
            for button in buttons:
                if button.url:
                    # URL button
                    actions.append({
                        "type": "button",
                        "text": {"type": "plain_text", "text": button.text},
                        "url": button.url,
                        "style": self._map_button_style(button.style),
                    })
                else:
                    # Action button
                    actions.append({
                        "type": "button",
                        "text": {"type": "plain_text", "text": button.text},
                        "value": button.callback_data,
                        "action_id": button.callback_data,
                        "style": self._map_button_style(button.style),
                    })

            if actions:
                blocks.append({"type": "actions", "elements": actions})

        # Send message
        result = await self.app.client.chat_postMessage(
            channel=chat_id,
            text=text,  # Fallback text
            blocks=blocks,
            thread_ts=thread_id or reply_to_message_id,
        )

        return result["ts"]  # message timestamp (serves as message ID)

    async def edit_message(
        self,
        chat_id: str,
        message_id: str,  # message timestamp
        text: str,
        buttons: Optional[List[MessageButton]] = None,
    ) -> None:
        """Edit an existing Slack message."""
        if not self.app:
            raise RuntimeError("Slack channel not started")

        # Build blocks
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            }
        ]

        if buttons:
            actions = []
            for button in buttons:
                if button.url:
                    actions.append({
                        "type": "button",
                        "text": {"type": "plain_text", "text": button.text},
                        "url": button.url,
                        "style": self._map_button_style(button.style),
                    })
                else:
                    actions.append({
                        "type": "button",
                        "text": {"type": "plain_text", "text": button.text},
                        "value": button.callback_data,
                        "action_id": button.callback_data,
                        "style": self._map_button_style(button.style),
                    })

            if actions:
                blocks.append({"type": "actions", "elements": actions})

        await self.app.client.chat_update(
            channel=chat_id,
            ts=message_id,
            text=text,
            blocks=blocks,
        )

    async def delete_message(self, chat_id: str, message_id: str) -> None:
        """Delete a Slack message."""
        if not self.app:
            raise RuntimeError("Slack channel not started")

        await self.app.client.chat_delete(
            channel=chat_id,
            ts=message_id,
        )

    async def react_to_message(self, chat_id: str, message_id: str, emoji: str) -> None:
        """
        React to a message with an emoji.

        Slack reactions use emoji names without colons (e.g., "thumbsup" not ":thumbsup:")
        """
        if not self.app:
            raise RuntimeError("Slack channel not started")

        # Strip colons if present
        emoji_name = emoji.strip(":")

        try:
            await self.app.client.reactions_add(
                channel=chat_id,
                timestamp=message_id,
                name=emoji_name,
            )
        except Exception as e:
            logger.warning(f"Failed to react to message: {e}")

    async def start(self) -> None:
        """
        Start the Slack bot.

        Uses Socket Mode if app_token is provided, otherwise uses Events API.
        """
        logger.info("Starting Slack channel...")

        # Build app
        self.app = AsyncApp(token=self.bot_token)

        # Register handlers
        self.app.message("")(self._handle_message_event)  # All messages
        self.app.action({"action_id": ".*"})(self._handle_button_action)  # All button actions

        # Start in Socket Mode if app token provided
        if self.app_token:
            logger.info("Starting Slack in Socket Mode")
            self.handler = AsyncSocketModeHandler(self.app, self.app_token)
            await self.handler.connect_async()
            logger.info("Slack channel started (Socket Mode)")
        else:
            logger.info("Slack app initialized (Events API mode)")
            logger.info("Slack channel started")

    async def stop(self) -> None:
        """Stop the Slack bot."""
        if self.handler:
            logger.info("Stopping Slack channel...")
            await self.handler.close_async()
            logger.info("Slack channel stopped")

    # Internal handlers

    async def _handle_message_event(self, event, say, client):
        """Handle incoming Slack messages."""
        # Skip bot messages
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return

        # Get user info
        user_id = event.get("user")
        channel_id = event.get("channel")
        text = event.get("text", "")
        ts = event.get("ts")
        thread_ts = event.get("thread_ts")

        # Get user profile
        try:
            user_info = await client.users_info(user=user_id)
            user_name = user_info["user"]["real_name"] or user_info["user"]["name"]
        except Exception:
            user_name = "Unknown"

        # Check if it's a DM
        channel_info = await client.conversations_info(channel=channel_id)
        is_group = channel_info["channel"]["is_channel"] or channel_info["channel"]["is_group"]

        # Build message context
        ctx = MessageContext(
            platform="slack",
            user_id=user_id,
            user_name=user_name,
            chat_id=channel_id,
            message_id=ts,
            text=text,
            is_group=is_group,
            thread_id=thread_ts,
            raw_update=event,
        )

        # Dispatch to registered handlers
        await self._handle_message(ctx)

    async def _handle_button_action(self, ack, action, body, client):
        """Handle button click actions."""
        await ack()  # Acknowledge the action

        user_id = body["user"]["id"]
        user_name = body["user"]["username"]
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        action_value = action.get("value", "")

        # Build message context
        ctx = MessageContext(
            platform="slack",
            user_id=user_id,
            user_name=user_name,
            chat_id=channel_id,
            message_id=message_ts,
            text=action_value,  # Use action value as text
            is_group=False,  # Button clicks are typically in context
            raw_update=body,
        )

        # Dispatch to button handler
        if action_value:
            await self._handle_button_click(ctx, action_value)

    def _map_button_style(self, style: ButtonStyle) -> Optional[str]:
        """Map ButtonStyle to Slack button style."""
        mapping = {
            ButtonStyle.PRIMARY: "primary",
            ButtonStyle.SECONDARY: None,  # Default
            ButtonStyle.SUCCESS: None,  # Slack doesn't have success style
            ButtonStyle.DANGER: "danger",
        }
        return mapping.get(style)
