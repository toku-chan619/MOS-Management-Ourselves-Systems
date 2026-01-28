"""
Telegram Bot integration.

Inspired by molt.bot's Telegram implementation (src/telegram/bot.ts)
using python-telegram-bot library.
"""
import logging
from typing import Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from app.core.logging import get_logger
from .base import MessagingChannel, MessageContext, MessageButton, ButtonStyle


logger = get_logger(__name__)


class TelegramChannel(MessagingChannel):
    """
    Telegram Bot implementation of MessagingChannel.

    Features inspired by molt.bot:
    - Message handling with context
    - Inline button support
    - Thread/topic support
    - Error handling and logging
    """

    def __init__(self, token: str, allowed_users: Optional[List[int]] = None):
        super().__init__("telegram")
        self.token = token
        self.allowed_users = allowed_users or []
        self.app: Optional[Application] = None

    async def send_message(
        self,
        chat_id: str,
        text: str,
        buttons: Optional[List[MessageButton]] = None,
        reply_to_message_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> str:
        """Send a message to Telegram."""
        if not self.app:
            raise RuntimeError("Telegram channel not started")

        # Build inline keyboard if buttons provided
        reply_markup = None
        if buttons:
            keyboard = []
            row = []
            for button in buttons:
                if button.url:
                    btn = InlineKeyboardButton(button.text, url=button.url)
                else:
                    btn = InlineKeyboardButton(button.text, callback_data=button.callback_data)
                row.append(btn)
                # 2 buttons per row
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:  # Add remaining buttons
                keyboard.append(row)
            reply_markup = InlineKeyboardMarkup(keyboard)

        # Send message
        message = await self.app.bot.send_message(
            chat_id=int(chat_id),
            text=text,
            reply_markup=reply_markup,
            reply_to_message_id=int(reply_to_message_id) if reply_to_message_id else None,
            message_thread_id=int(thread_id) if thread_id else None,
        )

        return str(message.message_id)

    async def edit_message(
        self,
        chat_id: str,
        message_id: str,
        text: str,
        buttons: Optional[List[MessageButton]] = None,
    ) -> None:
        """Edit an existing Telegram message."""
        if not self.app:
            raise RuntimeError("Telegram channel not started")

        reply_markup = None
        if buttons:
            keyboard = []
            row = []
            for button in buttons:
                if button.url:
                    btn = InlineKeyboardButton(button.text, url=button.url)
                else:
                    btn = InlineKeyboardButton(button.text, callback_data=button.callback_data)
                row.append(btn)
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            reply_markup = InlineKeyboardMarkup(keyboard)

        await self.app.bot.edit_message_text(
            chat_id=int(chat_id),
            message_id=int(message_id),
            text=text,
            reply_markup=reply_markup,
        )

    async def delete_message(self, chat_id: str, message_id: str) -> None:
        """Delete a Telegram message."""
        if not self.app:
            raise RuntimeError("Telegram channel not started")

        await self.app.bot.delete_message(
            chat_id=int(chat_id),
            message_id=int(message_id),
        )

    async def react_to_message(self, chat_id: str, message_id: str, emoji: str) -> None:
        """
        React to a message (Telegram supports reactions).

        Note: Requires Telegram Bot API 7.0+
        """
        if not self.app:
            raise RuntimeError("Telegram channel not started")

        try:
            await self.app.bot.set_message_reaction(
                chat_id=int(chat_id),
                message_id=int(message_id),
                reaction=[{"type": "emoji", "emoji": emoji}],
            )
        except Exception as e:
            logger.warning(f"Failed to react to message: {e}")

    async def start(self) -> None:
        """
        Start the Telegram bot.

        Sets up handlers and begins polling for updates.
        """
        logger.info("Starting Telegram channel...")

        # Build application
        self.app = Application.builder().token(self.token).build()

        # Register handlers
        self.app.add_handler(CommandHandler("start", self._handle_start_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text_message))
        self.app.add_handler(CallbackQueryHandler(self._handle_button_callback))

        # Error handler
        self.app.add_error_handler(self._handle_error)

        # Start polling
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        logger.info("Telegram channel started")

    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self.app:
            logger.info("Stopping Telegram channel...")
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            logger.info("Telegram channel stopped")

    # Internal handlers

    async def _handle_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not update.effective_user or not update.effective_chat:
            return

        # Check if user is allowed
        if self.allowed_users and update.effective_user.id not in self.allowed_users:
            await update.message.reply_text(
                "Sorry, you are not authorized to use this bot."
            )
            return

        await update.message.reply_text(
            "Welcome to MOS (Management Ourselves System)!\n\n"
            "Send me a message to create a task."
        )

    async def _handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages."""
        if not update.effective_user or not update.effective_chat or not update.message:
            return

        # Check if user is allowed
        if self.allowed_users and update.effective_user.id not in self.allowed_users:
            return

        # Build message context
        ctx = MessageContext(
            platform="telegram",
            user_id=str(update.effective_user.id),
            user_name=update.effective_user.full_name or "Unknown",
            chat_id=str(update.effective_chat.id),
            message_id=str(update.message.message_id),
            text=update.message.text or "",
            is_group=update.effective_chat.type in ["group", "supergroup"],
            thread_id=str(update.message.message_thread_id) if update.message.message_thread_id else None,
            raw_update=update,
        )

        # Dispatch to registered handlers
        await self._handle_message(ctx)

    async def _handle_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline button callbacks."""
        if not update.callback_query or not update.effective_user or not update.effective_chat:
            return

        query = update.callback_query
        await query.answer()  # Acknowledge the callback

        # Check if user is allowed
        if self.allowed_users and update.effective_user.id not in self.allowed_users:
            return

        # Build message context
        ctx = MessageContext(
            platform="telegram",
            user_id=str(update.effective_user.id),
            user_name=update.effective_user.full_name or "Unknown",
            chat_id=str(update.effective_chat.id),
            message_id=str(query.message.message_id) if query.message else "",
            text=query.data or "",
            is_group=update.effective_chat.type in ["group", "supergroup"],
            raw_update=update,
        )

        # Dispatch to button handler
        if query.data:
            await self._handle_button_click(ctx, query.data)

    async def _handle_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors."""
        logger.error(f"Telegram bot error: {context.error}", exc_info=context.error)
