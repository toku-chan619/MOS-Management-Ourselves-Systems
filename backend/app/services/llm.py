"""
LLM service with provider abstraction.

This module provides a unified interface for calling LLMs,
supporting multiple backends (OpenAI API, Claude CLI, Ollama, etc.)
"""
from typing import Dict
from functools import lru_cache

from app.core.config import settings
from app.core.exceptions import LLMAPIError
from app.core.logging import get_logger
from app.services.llm_provider import LLMProvider, LLMBackend

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """
    Get the configured LLM provider.

    Returns:
        LLMProvider instance based on LLM_BACKEND setting

    Raises:
        LLMAPIError: When backend is not supported
    """
    backend = settings.LLM_BACKEND.lower()

    logger.info(
        "Initializing LLM provider",
        backend=backend
    )

    if backend == LLMBackend.OPENAI_API:
        from app.services.openai_provider import OpenAIProvider
        return OpenAIProvider()

    elif backend == LLMBackend.CLAUDE_CLI:
        from app.services.cli_provider import ClaudeCLIProvider
        return ClaudeCLIProvider()

    elif backend == LLMBackend.OLLAMA_CLI:
        from app.services.cli_provider import OllamaCLIProvider
        return OllamaCLIProvider()

    else:
        raise LLMAPIError(
            f"Unsupported LLM backend: {backend}",
            {
                "backend": backend,
                "supported": [b.value for b in LLMBackend]
            }
        )


async def call_llm_json(
    system_prompt: str,
    user_text: str,
    max_retries: int = 3,
    initial_delay: float = 1.0
) -> Dict:
    """
    Call LLM with JSON response format.

    This is the main entry point for LLM calls in the application.
    It uses the configured LLM backend (OpenAI API, Claude CLI, Ollama, etc.)

    Args:
        system_prompt: System prompt for the LLM
        user_text: User input text
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds

    Returns:
        Parsed JSON response from LLM

    Raises:
        LLMAPIError: When LLM call fails after all retries
    """
    provider = get_llm_provider()

    logger.info(
        "Calling LLM",
        backend=settings.LLM_BACKEND,
        model=provider.get_model_name()
    )

    try:
        result = await provider.call_json(
            system_prompt=system_prompt,
            user_text=user_text,
            max_retries=max_retries,
            initial_delay=initial_delay
        )

        logger.info(
            "LLM call successful",
            backend=settings.LLM_BACKEND,
            model=provider.get_model_name()
        )

        return result

    except LLMAPIError:
        # Re-raise LLM errors as-is
        raise

    except Exception as e:
        logger.exception(
            "Unexpected error in LLM service",
            error=str(e)
        )
        raise LLMAPIError(
            f"Unexpected error: {str(e)}",
            {"type": type(e).__name__}
        )
