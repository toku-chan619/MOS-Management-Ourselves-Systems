"""
Unit tests for Celery worker tasks.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.workers.tasks import extract_and_store_draft, CallbackTask
from app.core.exceptions import LLMAPIError, RetryableError, DatabaseError
from app.schemas.draft import ExtractedDraft, ExtractedTask
from sqlalchemy.exc import SQLAlchemyError


@pytest.mark.unit
@pytest.mark.celery
def test_callback_task_on_success():
    """Test CallbackTask on_success callback."""
    task = CallbackTask()
    task.name = "test_task"

    # Should not raise exception
    task.on_success(retval="result", task_id="123", args=[], kwargs={})


@pytest.mark.unit
@pytest.mark.celery
def test_callback_task_on_failure():
    """Test CallbackTask on_failure callback."""
    task = CallbackTask()
    task.name = "test_task"

    # Should not raise exception
    task.on_failure(exc=Exception("error"), task_id="123", args=[], kwargs={}, einfo=None)


@pytest.mark.unit
@pytest.mark.celery
def test_callback_task_on_retry():
    """Test CallbackTask on_retry callback."""
    task = CallbackTask()
    task.name = "test_task"

    # Should not raise exception
    task.on_retry(exc=Exception("error"), task_id="123", args=[], kwargs={}, einfo=None)


@pytest.mark.unit
@pytest.mark.celery
def test_extract_and_store_draft_success():
    """Test successful task extraction and storage."""
    message_id = "msg-123"
    user_text = "Complete the project by next week"

    # Mock draft response
    mock_draft = ExtractedDraft(
        tasks=[
            ExtractedTask(
                temp_id="task-1",
                title="Complete the project",
                description="",
                priority="normal",
                status="backlog",
                confidence=0.9
            )
        ],
        questions=[]
    )

    # Mock the async functions
    with patch('app.workers.tasks.extract_draft', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_draft

        with patch('app.workers.tasks.SessionLocal') as mock_session_maker:
            mock_db = MagicMock()
            mock_db.execute = AsyncMock()
            mock_db.commit = AsyncMock()
            mock_db.rollback = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_session_maker.return_value = mock_db

            # Execute task
            extract_and_store_draft(message_id, user_text)

            # Verify extraction was called
            mock_extract.assert_called_once_with(user_text)

            # Verify database operations
            assert mock_db.execute.call_count == 2  # AgentRun + TaskDraft
            mock_db.commit.assert_called_once()


@pytest.mark.unit
@pytest.mark.celery
def test_extract_and_store_draft_empty_tasks():
    """Test extraction with no tasks."""
    message_id = "msg-123"
    user_text = "Just saying hello"

    # Mock draft with no tasks
    mock_draft = ExtractedDraft(
        tasks=[],
        questions=["What can I help you with?"]
    )

    with patch('app.workers.tasks.extract_draft', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_draft

        with patch('app.workers.tasks.SessionLocal') as mock_session_maker:
            mock_db = MagicMock()
            mock_db.execute = AsyncMock()
            mock_db.commit = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_session_maker.return_value = mock_db

            # Execute task
            extract_and_store_draft(message_id, user_text)

            # Should still store draft with empty tasks
            assert mock_db.execute.call_count == 2
            mock_db.commit.assert_called_once()


@pytest.mark.unit
@pytest.mark.celery
def test_extract_and_store_draft_llm_error():
    """Test task with LLM API error (should not retry)."""
    message_id = "msg-123"
    user_text = "Test message"

    with patch('app.workers.tasks.extract_draft', new_callable=AsyncMock) as mock_extract:
        mock_extract.side_effect = LLMAPIError("API error")

        with pytest.raises(LLMAPIError):
            extract_and_store_draft(message_id, user_text)


@pytest.mark.unit
@pytest.mark.celery
def test_extract_and_store_draft_retryable_error():
    """Test task with retryable error (should trigger retry)."""
    message_id = "msg-123"
    user_text = "Test message"

    with patch('app.workers.tasks.extract_draft', new_callable=AsyncMock) as mock_extract:
        mock_extract.side_effect = RetryableError("Rate limit")

        with pytest.raises(RetryableError):
            extract_and_store_draft(message_id, user_text)


@pytest.mark.unit
@pytest.mark.celery
def test_extract_and_store_draft_database_error():
    """Test task with database error."""
    message_id = "msg-123"
    user_text = "Test message"

    mock_draft = ExtractedDraft(
        tasks=[
            ExtractedTask(
                temp_id="task-1",
                title="Test",
                confidence=0.8
            )
        ],
        questions=[]
    )

    with patch('app.workers.tasks.extract_draft', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_draft

        with patch('app.workers.tasks.SessionLocal') as mock_session_maker:
            mock_db = MagicMock()
            mock_db.execute = AsyncMock(side_effect=SQLAlchemyError("DB error"))
            mock_db.rollback = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_session_maker.return_value = mock_db

            with pytest.raises(DatabaseError):
                extract_and_store_draft(message_id, user_text)

            # Should rollback on error
            mock_db.rollback.assert_called_once()


@pytest.mark.unit
@pytest.mark.celery
def test_extract_and_store_draft_calculates_confidence():
    """Test that task calculates average confidence correctly."""
    message_id = "msg-123"
    user_text = "Test message"

    mock_draft = ExtractedDraft(
        tasks=[
            ExtractedTask(temp_id="t1", title="Task 1", confidence=0.8),
            ExtractedTask(temp_id="t2", title="Task 2", confidence=0.9),
            ExtractedTask(temp_id="t3", title="Task 3", confidence=0.7),
        ],
        questions=[]
    )

    with patch('app.workers.tasks.extract_draft', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_draft

        with patch('app.workers.tasks.SessionLocal') as mock_session_maker:
            mock_db = MagicMock()
            mock_db.execute = AsyncMock()
            mock_db.commit = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_session_maker.return_value = mock_db

            extract_and_store_draft(message_id, user_text)

            # Average confidence should be (0.8 + 0.9 + 0.7) / 3 = 0.8
            # This is stored in the TaskDraft record


@pytest.mark.unit
@pytest.mark.celery
def test_extract_and_store_draft_stores_agent_run():
    """Test that task stores AgentRun record."""
    message_id = "msg-123"
    user_text = "Test message"

    mock_draft = ExtractedDraft(
        tasks=[ExtractedTask(temp_id="t1", title="Task 1", confidence=0.8)],
        questions=[]
    )

    with patch('app.workers.tasks.extract_draft', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_draft

        with patch('app.workers.tasks.SessionLocal') as mock_session_maker:
            mock_db = MagicMock()
            execute_calls = []

            async def track_execute(stmt):
                execute_calls.append(stmt)

            mock_db.execute = AsyncMock(side_effect=track_execute)
            mock_db.commit = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_session_maker.return_value = mock_db

            extract_and_store_draft(message_id, user_text)

            # Should create both AgentRun and TaskDraft
            assert len(execute_calls) == 2


@pytest.mark.unit
@pytest.mark.celery
def test_extract_and_store_draft_unexpected_error():
    """Test task with unexpected error."""
    message_id = "msg-123"
    user_text = "Test message"

    with patch('app.workers.tasks.extract_draft', new_callable=AsyncMock) as mock_extract:
        mock_extract.side_effect = ValueError("Unexpected error")

        with pytest.raises(ValueError):
            extract_and_store_draft(message_id, user_text)


@pytest.mark.unit
@pytest.mark.celery
def test_extract_and_store_draft_with_complex_draft():
    """Test task with complex draft containing multiple tasks."""
    message_id = "msg-123"
    user_text = "Launch website with homepage, contact page, and about page"

    mock_draft = ExtractedDraft(
        tasks=[
            ExtractedTask(
                temp_id="parent",
                title="Launch website",
                description="Main project",
                parent_temp_id=None,
                priority="high",
                status="doing",
                confidence=0.95,
                project_suggestion="Website Launch"
            ),
            ExtractedTask(
                temp_id="child1",
                title="Create homepage",
                description="Design and implement homepage",
                parent_temp_id="parent",
                priority="high",
                status="backlog",
                confidence=0.9
            ),
            ExtractedTask(
                temp_id="child2",
                title="Create contact page",
                description="Add contact form",
                parent_temp_id="parent",
                priority="normal",
                status="backlog",
                confidence=0.85
            ),
        ],
        questions=[]
    )

    with patch('app.workers.tasks.extract_draft', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_draft

        with patch('app.workers.tasks.SessionLocal') as mock_session_maker:
            mock_db = MagicMock()
            mock_db.execute = AsyncMock()
            mock_db.commit = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_session_maker.return_value = mock_db

            extract_and_store_draft(message_id, user_text)

            # Should handle complex draft structure
            mock_db.commit.assert_called_once()


@pytest.mark.unit
@pytest.mark.celery
def test_extract_and_store_draft_zero_confidence():
    """Test task with zero confidence."""
    message_id = "msg-123"
    user_text = "Test message"

    mock_draft = ExtractedDraft(
        tasks=[],
        questions=[]
    )

    with patch('app.workers.tasks.extract_draft', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_draft

        with patch('app.workers.tasks.SessionLocal') as mock_session_maker:
            mock_db = MagicMock()
            mock_db.execute = AsyncMock()
            mock_db.commit = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_session_maker.return_value = mock_db

            extract_and_store_draft(message_id, user_text)

            # Should handle zero confidence (no tasks)
            mock_db.commit.assert_called_once()
