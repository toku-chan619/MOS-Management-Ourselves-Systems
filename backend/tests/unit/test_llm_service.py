"""
Unit tests for LLM service (provider abstraction layer).
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from openai import RateLimitError, APIConnectionError, APIError
from app.services.llm import call_llm_json, get_llm_provider
from app.core.exceptions import LLMAPIError, RetryableError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_llm_json_success():
    """Test successful LLM API call via provider."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"result": "success"}'
    mock_response.usage.total_tokens = 100

    with patch('app.services.openai_provider.AsyncOpenAI') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch('app.services.llm.get_llm_provider') as mock_get_provider:
            # Clear LRU cache
            get_llm_provider.cache_clear()

            result = await call_llm_json("system prompt", "user text")

            assert result == {"result": "success"}
            mock_client.chat.completions.create.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_llm_json_empty_response():
    """Test LLM API call with empty response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None

    with patch('app.services.llm.AsyncOpenAI') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with pytest.raises(LLMAPIError, match="Empty response from LLM"):
            await call_llm_json("system prompt", "user text")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_llm_json_invalid_json():
    """Test LLM API call with invalid JSON response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "not valid json"

    with patch('app.services.llm.AsyncOpenAI') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with pytest.raises(LLMAPIError, match="Invalid JSON response from LLM"):
            await call_llm_json("system prompt", "user text")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_llm_json_rate_limit_retry():
    """Test LLM API call with rate limit and retry."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"result": "success"}'
    mock_response.usage.total_tokens = 100

    with patch('app.services.llm.AsyncOpenAI') as mock_client_class:
        mock_client = AsyncMock()
        # First call raises RateLimitError, second succeeds
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[RateLimitError("Rate limit"), mock_response]
        )
        mock_client_class.return_value = mock_client

        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await call_llm_json("system prompt", "user text", initial_delay=0.01)

        assert result == {"result": "success"}
        assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_llm_json_rate_limit_exhausted():
    """Test LLM API call with rate limit exhausted."""
    with patch('app.services.llm.AsyncOpenAI') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError("Rate limit")
        )
        mock_client_class.return_value = mock_client

        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(RetryableError, match="Rate limit exceeded after all retries"):
                await call_llm_json("system prompt", "user text", max_retries=2, initial_delay=0.01)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_llm_json_connection_error_retry():
    """Test LLM API call with connection error and retry."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"result": "success"}'
    mock_response.usage.total_tokens = 100

    with patch('app.services.llm.AsyncOpenAI') as mock_client_class:
        mock_client = AsyncMock()
        # First call raises connection error, second succeeds
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[APIConnectionError("Connection failed"), mock_response]
        )
        mock_client_class.return_value = mock_client

        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await call_llm_json("system prompt", "user text", initial_delay=0.01)

        assert result == {"result": "success"}
        assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_llm_json_connection_error_exhausted():
    """Test LLM API call with connection error exhausted."""
    with patch('app.services.llm.AsyncOpenAI') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError("Connection failed")
        )
        mock_client_class.return_value = mock_client

        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(RetryableError, match="Connection error after all retries"):
                await call_llm_json("system prompt", "user text", max_retries=2, initial_delay=0.01)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_llm_json_api_error_401():
    """Test LLM API call with 401 error (no retry)."""
    with patch('app.services.llm.AsyncOpenAI') as mock_client_class:
        mock_client = AsyncMock()
        error = APIError("Invalid API key", response=MagicMock(), body=None)
        error.status_code = 401
        error.message = "Invalid API key"
        mock_client.chat.completions.create = AsyncMock(side_effect=error)
        mock_client_class.return_value = mock_client

        with pytest.raises(LLMAPIError, match="OpenAI API error"):
            await call_llm_json("system prompt", "user text")

        # Should not retry on 401
        assert mock_client.chat.completions.create.call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_llm_json_api_error_500_retry():
    """Test LLM API call with 500 error (retry)."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"result": "success"}'
    mock_response.usage.total_tokens = 100

    with patch('app.services.llm.AsyncOpenAI') as mock_client_class:
        mock_client = AsyncMock()
        error = APIError("Server error", response=MagicMock(), body=None)
        error.status_code = 500
        error.message = "Server error"
        # First call raises 500 error, second succeeds
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[error, mock_response]
        )
        mock_client_class.return_value = mock_client

        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await call_llm_json("system prompt", "user text", initial_delay=0.01)

        assert result == {"result": "success"}
        assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_llm_json_exponential_backoff():
    """Test LLM API call with exponential backoff delays."""
    with patch('app.services.llm.AsyncOpenAI') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError("Rate limit")
        )
        mock_client_class.return_value = mock_client

        sleep_times = []

        async def track_sleep(seconds):
            sleep_times.append(seconds)

        with patch('asyncio.sleep', new_callable=AsyncMock, side_effect=track_sleep):
            with pytest.raises(RetryableError):
                await call_llm_json("system prompt", "user text", max_retries=3, initial_delay=1.0)

        # Check exponential backoff: 1, 2, 4 (for attempts 0, 1, 2; but last retry doesn't sleep)
        assert len(sleep_times) == 2  # Only 2 sleeps for 3 retries
        assert sleep_times[0] == 1.0
        assert sleep_times[1] == 2.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_llm_json_missing_api_key():
    """Test LLM API call with missing API key."""
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.OPENAI_API_KEY = None

        with pytest.raises(LLMAPIError, match="OPENAI_API_KEY is not set"):
            await call_llm_json("system prompt", "user text")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_llm_json_unexpected_error():
    """Test LLM API call with unexpected error."""
    with patch('app.services.llm.AsyncOpenAI') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=ValueError("Unexpected error")
        )
        mock_client_class.return_value = mock_client

        with pytest.raises(LLMAPIError, match="Unexpected error"):
            await call_llm_json("system prompt", "user text")
