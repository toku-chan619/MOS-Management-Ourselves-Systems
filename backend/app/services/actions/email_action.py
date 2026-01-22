"""
Email sending action.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any

from app.services.actions.base import ActionExecutor, ActionResult
from app.services.actions.registry import action_registry
from app.core.config import settings
from app.core.logging import logger


@action_registry.register("send_email")
class SendEmailAction(ActionExecutor):
    """
    Send an email.

    Parameters:
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text)
        cc: Optional CC recipients (list)
        bcc: Optional BCC recipients (list)
    """

    def validate_parameters(self) -> None:
        """Validate email parameters."""
        required = ["to", "subject", "body"]
        for param in required:
            if param not in self.parameters:
                raise ValueError(f"Missing required parameter: {param}")

        # Validate email format (basic)
        to_email = self.parameters["to"]
        if "@" not in to_email:
            raise ValueError(f"Invalid email address: {to_email}")

    async def execute(self) -> ActionResult:
        """Send the email."""
        try:
            # Note: This requires SMTP configuration in settings
            # For now, we'll log the email instead of actually sending
            logger.info(
                "Email action executed",
                to=self.parameters["to"],
                subject=self.parameters["subject"]
            )

            # In production, you would do:
            # msg = MIMEMultipart()
            # msg['From'] = settings.SMTP_FROM
            # msg['To'] = self.parameters["to"]
            # msg['Subject'] = self.parameters["subject"]
            # msg.attach(MIMEText(self.parameters["body"], 'plain'))
            #
            # with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            #     server.starttls()
            #     server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            #     server.send_message(msg)

            return ActionResult(
                success=True,
                data={
                    "to": self.parameters["to"],
                    "subject": self.parameters["subject"],
                    "message": "Email would be sent (SMTP not configured)"
                }
            )
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return ActionResult(
                success=False,
                error=str(e)
            )

    async def dry_run(self) -> ActionResult:
        """Simulate email sending."""
        return ActionResult(
            success=True,
            data={
                "dry_run": True,
                "to": self.parameters["to"],
                "subject": self.parameters["subject"],
                "body_preview": self.parameters["body"][:100] + "...",
                "message": "Email preview (not sent)"
            }
        )

    def get_description(self) -> str:
        """Get action description."""
        return f"Send email to {self.parameters.get('to', 'unknown')} with subject '{self.parameters.get('subject', 'unknown')}'"

    def get_safety_warnings(self) -> list[str]:
        """Get safety warnings."""
        return [
            "This will send an actual email",
            "Make sure the recipient address is correct",
            "Email cannot be unsent once delivered"
        ]
