"""
CLI-based LLM providers (Claude CLI, Ollama, etc.)

These providers execute LLM via command-line interface.
Useful for Docker environments and local development.
"""
import json
import asyncio
from typing import Dict

from app.core.config import settings
from app.core.exceptions import LLMAPIError
from app.core.logging import get_logger
from app.services.llm_provider import LLMProvider

logger = get_logger(__name__)


class ClaudeCLIProvider(LLMProvider):
    """
    Claude CLI provider.

    Requires Claude CLI to be installed and authenticated.
    See: https://docs.anthropic.com/claude/docs/cli
    """

    def __init__(self):
        """Initialize Claude CLI provider."""
        self.cli_path = settings.CLAUDE_CLI_PATH
        self.model = "claude"

    def get_model_name(self) -> str:
        """Get the model name being used."""
        return self.model

    async def call_json(
        self,
        system_prompt: str,
        user_text: str,
        max_retries: int = 3,
        initial_delay: float = 1.0
    ) -> Dict:
        """
        Call Claude via CLI with JSON response format.

        Args:
            system_prompt: System prompt for the LLM
            user_text: User input text
            max_retries: Maximum number of retry attempts (not used for CLI)
            initial_delay: Initial delay between retries (not used for CLI)

        Returns:
            Parsed JSON response from LLM

        Raises:
            LLMAPIError: When CLI call fails
        """
        logger.info("Calling Claude CLI", model=self.model)

        try:
            # Construct prompt with system message and user message
            full_prompt = f"{system_prompt}\n\n{user_text}"

            # Create subprocess
            proc = await asyncio.create_subprocess_exec(
                self.cli_path,
                "--format", "json",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Send prompt and get response
            stdout, stderr = await proc.communicate(input=full_prompt.encode())

            if proc.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(
                    "Claude CLI failed",
                    returncode=proc.returncode,
                    error=error_msg
                )
                raise LLMAPIError(
                    f"Claude CLI failed: {error_msg}",
                    {"returncode": proc.returncode}
                )

            # Parse JSON response
            result = json.loads(stdout.decode())

            logger.info("Claude CLI call successful")
            return result

        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse JSON response from Claude CLI",
                error=str(e)
            )
            raise LLMAPIError(
                "Invalid JSON response from Claude CLI",
                {"error": str(e)}
            )

        except FileNotFoundError:
            logger.error(
                "Claude CLI not found",
                cli_path=self.cli_path
            )
            raise LLMAPIError(
                f"Claude CLI not found at: {self.cli_path}",
                {"cli_path": self.cli_path}
            )

        except Exception as e:
            logger.exception(
                "Unexpected error calling Claude CLI",
                error=str(e)
            )
            raise LLMAPIError(
                f"Unexpected error: {str(e)}",
                {"type": type(e).__name__}
            )


class OllamaCLIProvider(LLMProvider):
    """
    Ollama CLI provider.

    Requires Ollama to be installed and running.
    See: https://ollama.ai/
    """

    def __init__(self):
        """Initialize Ollama CLI provider."""
        self.cli_path = settings.OLLAMA_CLI_PATH
        self.model = settings.OLLAMA_MODEL

    def get_model_name(self) -> str:
        """Get the model name being used."""
        return self.model

    async def call_json(
        self,
        system_prompt: str,
        user_text: str,
        max_retries: int = 3,
        initial_delay: float = 1.0
    ) -> Dict:
        """
        Call Ollama via CLI with JSON response format.

        Args:
            system_prompt: System prompt for the LLM
            user_text: User input text
            max_retries: Maximum number of retry attempts (not used for CLI)
            initial_delay: Initial delay between retries (not used for CLI)

        Returns:
            Parsed JSON response from LLM

        Raises:
            LLMAPIError: When CLI call fails
        """
        logger.info("Calling Ollama CLI", model=self.model)

        try:
            # Construct prompt with system message and user message
            full_prompt = f"{system_prompt}\n\n{user_text}"

            # Create subprocess
            proc = await asyncio.create_subprocess_exec(
                self.cli_path,
                "run",
                self.model,
                "--format", "json",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Send prompt and get response
            stdout, stderr = await proc.communicate(input=full_prompt.encode())

            if proc.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(
                    "Ollama CLI failed",
                    returncode=proc.returncode,
                    error=error_msg
                )
                raise LLMAPIError(
                    f"Ollama CLI failed: {error_msg}",
                    {"returncode": proc.returncode}
                )

            # Parse JSON response
            result = json.loads(stdout.decode())

            logger.info("Ollama CLI call successful")
            return result

        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse JSON response from Ollama CLI",
                error=str(e)
            )
            raise LLMAPIError(
                "Invalid JSON response from Ollama CLI",
                {"error": str(e)}
            )

        except FileNotFoundError:
            logger.error(
                "Ollama CLI not found",
                cli_path=self.cli_path
            )
            raise LLMAPIError(
                f"Ollama CLI not found at: {self.cli_path}",
                {"cli_path": self.cli_path}
            )

        except Exception as e:
            logger.exception(
                "Unexpected error calling Ollama CLI",
                error=str(e)
            )
            raise LLMAPIError(
                f"Unexpected error: {str(e)}",
                {"type": type(e).__name__}
            )
