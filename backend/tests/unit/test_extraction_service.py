"""
Unit tests for extraction service.
"""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import date, time
from app.services.extraction import extract_draft
from app.schemas.draft import ExtractedDraft
from pydantic import ValidationError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_draft_success():
    """Test successful task extraction."""
    mock_llm_response = {
        "tasks": [
            {
                "temp_id": "task-1",
                "parent_temp_id": None,
                "title": "Complete project proposal",
                "description": "Write and submit the Q1 project proposal",
                "project_suggestion": "Q1 Projects",
                "due_date": "2026-02-01",
                "due_time": "17:00:00",
                "priority": "high",
                "status": "backlog",
                "assumptions": ["Budget approval is ready"],
                "questions": [],
                "confidence": 0.9
            }
        ],
        "questions": []
    }

    with patch('app.services.extraction.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_response

        result = await extract_draft("I need to complete the project proposal by Feb 1st")

        assert isinstance(result, ExtractedDraft)
        assert len(result.tasks) == 1
        assert result.tasks[0].temp_id == "task-1"
        assert result.tasks[0].title == "Complete project proposal"
        assert result.tasks[0].priority == "high"
        assert result.tasks[0].due_date == date(2026, 2, 1)
        assert result.tasks[0].due_time == time(17, 0, 0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_draft_with_hierarchy():
    """Test task extraction with parent-child hierarchy."""
    mock_llm_response = {
        "tasks": [
            {
                "temp_id": "parent-1",
                "parent_temp_id": None,
                "title": "Launch website",
                "description": "Launch the new company website",
                "project_suggestion": "Website",
                "due_date": None,
                "due_time": None,
                "priority": "high",
                "status": "doing",
                "assumptions": [],
                "questions": [],
                "confidence": 0.95
            },
            {
                "temp_id": "child-1",
                "parent_temp_id": "parent-1",
                "title": "Design homepage",
                "description": "Create homepage design mockup",
                "project_suggestion": None,
                "due_date": "2026-02-15",
                "due_time": None,
                "priority": "normal",
                "status": "backlog",
                "assumptions": [],
                "questions": [],
                "confidence": 0.85
            }
        ],
        "questions": []
    }

    with patch('app.services.extraction.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_response

        result = await extract_draft("Launch website. First design the homepage by Feb 15.")

        assert len(result.tasks) == 2
        assert result.tasks[0].parent_temp_id is None
        assert result.tasks[1].parent_temp_id == "parent-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_draft_no_tasks():
    """Test extraction with no tasks found."""
    mock_llm_response = {
        "tasks": [],
        "questions": ["Could you clarify what you need help with?"]
    }

    with patch('app.services.extraction.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_response

        result = await extract_draft("Just saying hello")

        assert len(result.tasks) == 0
        assert len(result.questions) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_draft_with_questions():
    """Test extraction with clarifying questions."""
    mock_llm_response = {
        "tasks": [
            {
                "temp_id": "task-1",
                "parent_temp_id": None,
                "title": "Schedule meeting",
                "description": "Schedule the team meeting",
                "project_suggestion": None,
                "due_date": None,
                "due_time": None,
                "priority": "normal",
                "status": "backlog",
                "assumptions": [],
                "questions": ["What date did you have in mind?"],
                "confidence": 0.6
            }
        ],
        "questions": ["What date did you have in mind?"]
    }

    with patch('app.services.extraction.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_response

        result = await extract_draft("Schedule a team meeting")

        assert len(result.tasks) == 1
        assert len(result.questions) == 1
        assert result.tasks[0].confidence == 0.6


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_draft_invalid_schema():
    """Test extraction with invalid schema (should raise ValidationError)."""
    # Missing required field 'temp_id'
    mock_llm_response = {
        "tasks": [
            {
                "title": "Invalid task",
                "confidence": 0.5
            }
        ],
        "questions": []
    }

    with patch('app.services.extraction.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_response

        with pytest.raises(ValidationError):
            await extract_draft("Test message")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_draft_invalid_priority():
    """Test extraction with invalid priority value."""
    mock_llm_response = {
        "tasks": [
            {
                "temp_id": "task-1",
                "parent_temp_id": None,
                "title": "Task",
                "description": "",
                "project_suggestion": None,
                "due_date": None,
                "due_time": None,
                "priority": "invalid",  # Invalid value
                "status": "backlog",
                "assumptions": [],
                "questions": [],
                "confidence": 0.8
            }
        ],
        "questions": []
    }

    with patch('app.services.extraction.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_response

        with pytest.raises(ValidationError):
            await extract_draft("Test message")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_draft_invalid_confidence():
    """Test extraction with invalid confidence value."""
    mock_llm_response = {
        "tasks": [
            {
                "temp_id": "task-1",
                "parent_temp_id": None,
                "title": "Task",
                "description": "",
                "project_suggestion": None,
                "due_date": None,
                "due_time": None,
                "priority": "normal",
                "status": "backlog",
                "assumptions": [],
                "questions": [],
                "confidence": 1.5  # Out of range
            }
        ],
        "questions": []
    }

    with patch('app.services.extraction.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_response

        with pytest.raises(ValidationError):
            await extract_draft("Test message")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_draft_with_all_priorities():
    """Test extraction with all valid priority levels."""
    priorities = ["low", "normal", "high", "urgent"]

    for priority in priorities:
        mock_llm_response = {
            "tasks": [
                {
                    "temp_id": f"task-{priority}",
                    "parent_temp_id": None,
                    "title": f"Task with {priority} priority",
                    "description": "",
                    "project_suggestion": None,
                    "due_date": None,
                    "due_time": None,
                    "priority": priority,
                    "status": "backlog",
                    "assumptions": [],
                    "questions": [],
                    "confidence": 0.8
                }
            ],
            "questions": []
        }

        with patch('app.services.extraction.call_llm_json', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            result = await extract_draft(f"Test {priority}")

            assert result.tasks[0].priority == priority


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_draft_with_all_statuses():
    """Test extraction with all valid status values."""
    statuses = ["backlog", "doing", "waiting"]

    for status in statuses:
        mock_llm_response = {
            "tasks": [
                {
                    "temp_id": f"task-{status}",
                    "parent_temp_id": None,
                    "title": f"Task with {status} status",
                    "description": "",
                    "project_suggestion": None,
                    "due_date": None,
                    "due_time": None,
                    "priority": "normal",
                    "status": status,
                    "assumptions": [],
                    "questions": [],
                    "confidence": 0.8
                }
            ],
            "questions": []
        }

        with patch('app.services.extraction.call_llm_json', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            result = await extract_draft(f"Test {status}")

            assert result.tasks[0].status == status


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_draft_with_complex_data():
    """Test extraction with complex task data."""
    mock_llm_response = {
        "tasks": [
            {
                "temp_id": "task-complex",
                "parent_temp_id": None,
                "title": "Complex task",
                "description": "A task with all fields populated",
                "project_suggestion": "Important Project",
                "due_date": "2026-12-31",
                "due_time": "23:59:59",
                "priority": "urgent",
                "status": "doing",
                "assumptions": [
                    "Budget is approved",
                    "Team is available",
                    "Tools are ready"
                ],
                "questions": [
                    "Should we include testing?",
                    "What's the timeline?"
                ],
                "confidence": 0.75
            }
        ],
        "questions": ["Overall, is this timeline realistic?"]
    }

    with patch('app.services.extraction.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_response

        result = await extract_draft("Complex task description")

        task = result.tasks[0]
        assert task.title == "Complex task"
        assert task.project_suggestion == "Important Project"
        assert len(task.assumptions) == 3
        assert len(task.questions) == 2
        assert task.confidence == 0.75
        assert len(result.questions) == 1
