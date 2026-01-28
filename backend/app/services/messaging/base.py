"""
Base classes for messaging channel integration.

Inspired by molt.bot's channel abstraction pattern.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable, Awaitable
from enum import Enum


class ButtonStyle(str, Enum):
    """Button visual style."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    DANGER = "danger"


@dataclass
class MessageButton:
    """
    Inline button for messages.

    Inspired by molt.bot's button abstraction.
    """
    text: str
    callback_data: str
    style: ButtonStyle = ButtonStyle.SECONDARY
    url: Optional[str] = None


@dataclass
class MessageContext:
    """
    Context information for incoming messages.

    Provides unified interface across different messaging platforms.
    """
    platform: str  # "telegram", "slack", etc.
    user_id: str
    user_name: str
    chat_id: str
    message_id: str
    text: str
    is_group: bool = False
    thread_id: Optional[str] = None
    raw_update: Optional[Any] = None  # Platform-specific raw data


class MessagingChannel(ABC):
    """
    Abstract base class for messaging platform integration.

    Inspired by molt.bot's channel pattern:
    - Unified interface for send/receive
    - Platform-agnostic message handling
    - Support for rich UI (buttons, etc.)
    """

    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self._message_handlers: List[Callable[[MessageContext], Awaitable[None]]] = []
        self._button_handlers: Dict[str, Callable[[MessageContext, str], Awaitable[None]]] = {}

    @abstractmethod
    async def send_message(
        self,
        chat_id: str,
        text: str,
        buttons: Optional[List[MessageButton]] = None,
        reply_to_message_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> str:
        """
        Send a message to the specified chat.

        Args:
            chat_id: Chat/channel identifier
            text: Message text
            buttons: Optional inline buttons
            reply_to_message_id: Optional message to reply to
            thread_id: Optional thread/topic identifier

        Returns:
            Message ID of the sent message
        """
        pass

    @abstractmethod
    async def edit_message(
        self,
        chat_id: str,
        message_id: str,
        text: str,
        buttons: Optional[List[MessageButton]] = None,
    ) -> None:
        """Edit an existing message."""
        pass

    @abstractmethod
    async def delete_message(
        self,
        chat_id: str,
        message_id: str,
    ) -> None:
        """Delete a message."""
        pass

    @abstractmethod
    async def react_to_message(
        self,
        chat_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Add a reaction to a message."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """
        Start the messaging channel.

        This should set up webhooks or polling to receive messages.
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the messaging channel."""
        pass

    def on_message(self, handler: Callable[[MessageContext], Awaitable[None]]) -> None:
        """
        Register a message handler.

        Example:
            @channel.on_message
            async def handle_message(ctx: MessageContext):
                await channel.send_message(ctx.chat_id, f"Received: {ctx.text}")
        """
        self._message_handlers.append(handler)

    def on_button_click(
        self,
        callback_data: str,
        handler: Callable[[MessageContext, str], Awaitable[None]]
    ) -> None:
        """
        Register a button click handler.

        Args:
            callback_data: Button callback data to match
            handler: Handler function (ctx, data)
        """
        self._button_handlers[callback_data] = handler

    async def _handle_message(self, ctx: MessageContext) -> None:
        """
        Internal method to dispatch messages to handlers.

        Called by platform-specific implementations.
        """
        for handler in self._message_handlers:
            try:
                await handler(ctx)
            except Exception as e:
                # Log but don't crash
                print(f"Error in message handler: {e}")

    async def _handle_button_click(self, ctx: MessageContext, callback_data: str) -> None:
        """
        Internal method to dispatch button clicks to handlers.

        Called by platform-specific implementations.
        """
        handler = self._button_handlers.get(callback_data)
        if handler:
            try:
                await handler(ctx, callback_data)
            except Exception as e:
                print(f"Error in button handler: {e}")
