"""
LLM Provider abstraction layer.

Supports multiple LLM backends (OpenAI API, Claude CLI, Ollama, etc.)
"""
from abc import ABC, abstractmethod
from typing import Dict
from enum import Enum


class LLMBackend(str, Enum):
    """Supported LLM backends."""
    OPENAI_API = "openai_api"
    CLAUDE_CLI = "claude_cli"
    OLLAMA_CLI = "ollama_cli"


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def call_json(
        self,
        system_prompt: str,
        user_text: str,
        max_retries: int = 3,
        initial_delay: float = 1.0
    ) -> Dict:
        """
        Call LLM with JSON response format.

        Args:
            system_prompt: System prompt for the LLM
            user_text: User input text
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds

        Returns:
            Parsed JSON response from LLM

        Raises:
            LLMAPIError: When LLM call fails
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name being used."""
        pass
