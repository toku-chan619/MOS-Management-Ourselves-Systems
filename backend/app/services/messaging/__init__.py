"""
Messaging integration services.

Multi-platform messaging support inspired by molt.bot architecture.
"""
from .base import MessagingChannel, MessageContext, MessageButton, ButtonStyle
from .manager import MessagingManager
from .telegram import TelegramChannel
from .slack import SlackChannel
from .integration import MessagingIntegration

__all__ = [
    "MessagingChannel",
    "MessageContext",
    "MessageButton",
    "ButtonStyle",
    "MessagingManager",
    "TelegramChannel",
    "SlackChannel",
    "MessagingIntegration",
]
