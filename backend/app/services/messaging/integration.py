"""
Integration layer between messaging channels and MOS core.

Handles:
- Task creation from messages
- Task notifications to messaging platforms
- Button interactions for task operations
"""
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.draft import Draft, DraftStatus
from .base import MessageContext, MessageButton, ButtonStyle
from .manager import MessagingManager


logger = get_logger(__name__)


class MessagingIntegration:
    """
    Integration service connecting messaging platforms with MOS.

    Features:
    - Auto-create tasks from messages
    - Send notifications on task updates
    - Handle inline button interactions
    """

    def __init__(self, manager: MessagingManager, db: Session):
        self.manager = manager
        self.db = db

    async def handle_incoming_message(self, ctx: MessageContext) -> None:
        """
        Handle incoming message from any platform.

        Creates a task from the message content.
        """
        try:
            logger.info(
                f"Received message from {ctx.platform}:{ctx.user_name} in chat {ctx.chat_id}"
            )

            # Skip empty messages
            if not ctx.text.strip():
                return

            # Create task from message
            task = await self._create_task_from_message(ctx)

            # Send confirmation with action buttons
            channel = self.manager.get_channel(ctx.platform)
            if channel:
                await self._send_task_confirmation(channel, ctx, task)

            logger.info(f"Created task {task.id} from message")

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            # Try to send error message to user
            try:
                channel = self.manager.get_channel(ctx.platform)
                if channel:
                    await channel.send_message(
                        ctx.chat_id,
                        f"❌ Error creating task: {str(e)}",
                        reply_to_message_id=ctx.message_id,
                    )
            except Exception:
                pass

    async def _create_task_from_message(self, ctx: MessageContext) -> Task:
        """Create a task from message context."""
        # Use first line as title, rest as description
        lines = ctx.text.strip().split("\n", 1)
        title = lines[0][:200]  # Limit title length
        description = lines[1] if len(lines) > 1 else ""

        # Create task
        task = Task(
            title=title,
            description=description,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            created_by=f"{ctx.platform}:{ctx.user_id}",
            metadata_={
                "source": ctx.platform,
                "source_user_id": ctx.user_id,
                "source_user_name": ctx.user_name,
                "source_chat_id": ctx.chat_id,
                "source_message_id": ctx.message_id,
            },
        )

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        return task

    async def _send_task_confirmation(
        self, channel, ctx: MessageContext, task: Task
    ) -> None:
        """Send task creation confirmation with action buttons."""
        # Build confirmation message
        message = (
            f"✅ Task created: #{task.id}\n\n"
            f"📋 {task.title}\n"
            f"📊 Status: {task.status.value}\n"
            f"🎯 Priority: {task.priority.value}"
        )

        if task.description:
            message += f"\n\n{task.description[:200]}"
            if len(task.description) > 200:
                message += "..."

        # Build action buttons
        buttons = [
            MessageButton(
                text="✓ Complete",
                callback_data=f"task_complete:{task.id}",
                style=ButtonStyle.PRIMARY,
            ),
            MessageButton(
                text="✕ Cancel",
                callback_data=f"task_cancel:{task.id}",
                style=ButtonStyle.DANGER,
            ),
            MessageButton(
                text="📝 Edit",
                callback_data=f"task_edit:{task.id}",
                style=ButtonStyle.SECONDARY,
            ),
            MessageButton(
                text="🔍 Details",
                url=f"http://localhost:3000/tasks/{task.id}",  # TODO: Make configurable
                style=ButtonStyle.SECONDARY,
            ),
        ]

        await channel.send_message(
            ctx.chat_id, message, buttons=buttons, reply_to_message_id=ctx.message_id
        )

    async def handle_button_click(
        self, ctx: MessageContext, callback_data: str
    ) -> None:
        """
        Handle button click from any platform.

        Callback data format: "action:task_id"
        """
        try:
            logger.info(f"Button clicked: {callback_data} by {ctx.user_name}")

            # Parse callback data
            parts = callback_data.split(":", 1)
            if len(parts) != 2:
                logger.warning(f"Invalid callback data: {callback_data}")
                return

            action, task_id_str = parts

            try:
                task_id = int(task_id_str)
            except ValueError:
                logger.warning(f"Invalid task ID: {task_id_str}")
                return

            # Get task
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                channel = self.manager.get_channel(ctx.platform)
                if channel:
                    await channel.send_message(
                        ctx.chat_id, f"❌ Task #{task_id} not found"
                    )
                return

            # Handle action
            if action == "task_complete":
                await self._handle_complete_task(ctx, task)
            elif action == "task_cancel":
                await self._handle_cancel_task(ctx, task)
            elif action == "task_edit":
                await self._handle_edit_task(ctx, task)
            else:
                logger.warning(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Error handling button click: {e}", exc_info=True)

    async def _handle_complete_task(self, ctx: MessageContext, task: Task) -> None:
        """Mark task as completed."""
        task.status = TaskStatus.DONE
        task.completed_at = datetime.utcnow()
        self.db.commit()

        channel = self.manager.get_channel(ctx.platform)
        if channel:
            await channel.send_message(
                ctx.chat_id, f"✅ Task #{task.id} marked as completed!"
            )
            # Also react to the original message
            if ctx.message_id:
                await channel.react_to_message(ctx.chat_id, ctx.message_id, "✅")

    async def _handle_cancel_task(self, ctx: MessageContext, task: Task) -> None:
        """Cancel task."""
        task.status = TaskStatus.CANCELLED
        self.db.commit()

        channel = self.manager.get_channel(ctx.platform)
        if channel:
            await channel.send_message(
                ctx.chat_id, f"❌ Task #{task.id} cancelled."
            )
            if ctx.message_id:
                await channel.react_to_message(ctx.chat_id, ctx.message_id, "❌")

    async def _handle_edit_task(self, ctx: MessageContext, task: Task) -> None:
        """Handle edit task request."""
        channel = self.manager.get_channel(ctx.platform)
        if channel:
            # For now, just send a link to edit in web UI
            message = (
                f"📝 Edit task #{task.id}:\n"
                f"Open: http://localhost:3000/tasks/{task.id}\n\n"
                f"Or reply with new task content to update."
            )
            await channel.send_message(ctx.chat_id, message)

    async def notify_task_update(
        self, task: Task, update_type: str, message: Optional[str] = None
    ) -> None:
        """
        Send notification about task update to original messaging platform.

        Args:
            task: The task that was updated
            update_type: Type of update (e.g., "completed", "updated", "assigned")
            message: Optional custom message
        """
        # Get source platform from task metadata
        if not task.metadata_ or "source" not in task.metadata_:
            logger.debug(f"Task {task.id} has no source platform, skipping notification")
            return

        platform = task.metadata_.get("source")
        chat_id = task.metadata_.get("source_chat_id")

        if not platform or not chat_id:
            logger.warning(f"Task {task.id} missing platform or chat_id")
            return

        # Get channel
        channel = self.manager.get_channel(platform)
        if not channel:
            logger.warning(f"Channel {platform} not found")
            return

        # Build notification message
        if not message:
            emoji_map = {
                "completed": "✅",
                "updated": "📝",
                "assigned": "👤",
                "cancelled": "❌",
                "deleted": "🗑️",
            }
            emoji = emoji_map.get(update_type, "📢")
            message = f"{emoji} Task #{task.id} {update_type}: {task.title}"

        # Send notification
        try:
            await channel.send_message(chat_id, message)
            logger.info(f"Sent notification for task {task.id} to {platform}:{chat_id}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
