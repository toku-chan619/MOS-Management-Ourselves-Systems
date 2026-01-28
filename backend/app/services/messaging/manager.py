"""
Messaging Manager for coordinating multiple messaging channels.

Inspired by molt.bot's gateway pattern (src/gateway.ts) but simplified for MOS.
"""
import asyncio
from typing import Dict, Optional, List
from app.core.logging import get_logger
from .base import MessagingChannel, MessageContext


logger = get_logger(__name__)


class MessagingManager:
    """
    Manages multiple messaging channels and coordinates their lifecycle.

    Features inspired by molt.bot:
    - Multi-channel support
    - Centralized lifecycle management
    - Unified message routing
    """

    def __init__(self):
        self.channels: Dict[str, MessagingChannel] = {}
        self._running = False

    def register_channel(self, channel: MessagingChannel) -> None:
        """Register a messaging channel."""
        if channel.name in self.channels:
            logger.warning(f"Channel {channel.name} already registered, replacing...")

        self.channels[channel.name] = channel
        logger.info(f"Registered channel: {channel.name}")

    def get_channel(self, name: str) -> Optional[MessagingChannel]:
        """Get a registered channel by name."""
        return self.channels.get(name)

    async def start_all(self) -> None:
        """Start all registered channels."""
        if self._running:
            logger.warning("Messaging manager already running")
            return

        logger.info(f"Starting {len(self.channels)} messaging channels...")

        # Start all channels concurrently
        tasks = []
        for name, channel in self.channels.items():
            logger.info(f"Starting channel: {name}")
            tasks.append(channel.start())

        await asyncio.gather(*tasks, return_exceptions=True)

        self._running = True
        logger.info("All messaging channels started")

    async def stop_all(self) -> None:
        """Stop all registered channels."""
        if not self._running:
            return

        logger.info(f"Stopping {len(self.channels)} messaging channels...")

        # Stop all channels concurrently
        tasks = []
        for name, channel in self.channels.items():
            logger.info(f"Stopping channel: {name}")
            tasks.append(channel.stop())

        await asyncio.gather(*tasks, return_exceptions=True)

        self._running = False
        logger.info("All messaging channels stopped")

    async def broadcast_message(
        self,
        text: str,
        chat_ids: Dict[str, str],  # {channel_name: chat_id}
        **kwargs
    ) -> Dict[str, str]:
        """
        Broadcast a message to multiple channels.

        Args:
            text: Message text
            chat_ids: Mapping of channel name to chat ID
            **kwargs: Additional parameters passed to send_message

        Returns:
            Mapping of channel name to message ID
        """
        results = {}
        tasks = []
        channel_names = []

        for channel_name, chat_id in chat_ids.items():
            channel = self.get_channel(channel_name)
            if not channel:
                logger.warning(f"Channel {channel_name} not found, skipping")
                continue

            tasks.append(channel.send_message(chat_id, text, **kwargs))
            channel_names.append(channel_name)

        if not tasks:
            logger.warning("No valid channels found for broadcast")
            return results

        # Execute all sends concurrently
        message_ids = await asyncio.gather(*tasks, return_exceptions=True)

        for channel_name, message_id in zip(channel_names, message_ids):
            if isinstance(message_id, Exception):
                logger.error(f"Failed to send to {channel_name}: {message_id}")
                results[channel_name] = None
            else:
                results[channel_name] = message_id

        return results

    def list_channels(self) -> List[str]:
        """List all registered channel names."""
        return list(self.channels.keys())

    @property
    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._running
