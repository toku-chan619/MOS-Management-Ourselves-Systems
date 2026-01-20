import json
import asyncio
from typing import Dict
from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError
from app.core.config import settings
from app.core.exceptions import LLMAPIError, RetryableError
from app.core.logging import get_logger

logger = get_logger(__name__)


async def call_llm_json(
    system_prompt: str,
    user_text: str,
    max_retries: int = 3,
    initial_delay: float = 1.0
) -> Dict:
    """
    Call OpenAI LLM API with JSON response format.
    Includes exponential backoff retry logic.

    Args:
        system_prompt: System prompt for the LLM
        user_text: User input text
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds

    Returns:
        Parsed JSON response from LLM

    Raises:
        LLMAPIError: When API call fails after all retries
    """
    if not settings.OPENAI_API_KEY:
        raise LLMAPIError("OPENAI_API_KEY is not set")

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    for attempt in range(max_retries):
        try:
            logger.info(
                "Calling OpenAI API",
                model=settings.LLM_MODEL,
                attempt=attempt + 1,
                max_retries=max_retries
            )

            resp = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            content = resp.choices[0].message.content
            if not content:
                raise LLMAPIError("Empty response from LLM")

            result = json.loads(content)

            logger.info(
                "OpenAI API call successful",
                tokens_used=resp.usage.total_tokens if resp.usage else 0
            )

            return result

        except RateLimitError as e:
            logger.warning(
                "Rate limit exceeded",
                attempt=attempt + 1,
                error=str(e)
            )
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                raise RetryableError(
                    "Rate limit exceeded after all retries",
                    {"attempts": max_retries, "error": str(e)}
                )

        except APIConnectionError as e:
            logger.warning(
                "API connection error",
                attempt=attempt + 1,
                error=str(e)
            )
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                raise RetryableError(
                    "Connection error after all retries",
                    {"attempts": max_retries, "error": str(e)}
                )

        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse JSON response",
                content=content if 'content' in locals() else None,
                error=str(e)
            )
            raise LLMAPIError(
                "Invalid JSON response from LLM",
                {"error": str(e)}
            )

        except APIError as e:
            logger.error(
                "OpenAI API error",
                attempt=attempt + 1,
                error=str(e)
            )
            # Don't retry on certain errors (e.g., invalid API key, model not found)
            if e.status_code in [401, 404]:
                raise LLMAPIError(
                    f"OpenAI API error: {e.message}",
                    {"status": e.status_code, "error": str(e)}
                )
            elif attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                raise LLMAPIError(
                    f"API error after all retries: {e.message}",
                    {"attempts": max_retries, "status": e.status_code}
                )

        except Exception as e:
            logger.exception(
                "Unexpected error calling OpenAI API",
                error=str(e)
            )
            raise LLMAPIError(
                f"Unexpected error: {str(e)}",
                {"type": type(e).__name__}
            )

    # Should never reach here, but just in case
    raise LLMAPIError("Failed to call LLM after all retries")
