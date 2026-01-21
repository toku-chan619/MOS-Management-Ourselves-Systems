"""
Integration tests for Followup API endpoints.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from app.models.task import Task
from datetime import date, time


@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_followup_morning(client: AsyncClient, async_session):
    """Test POST /api/followup/run - Morning slot."""
    # Create some tasks for context
    task = Task(
        title="Morning Task",
        description="Test task",
        status="doing",
        priority="high",
        due_date=date.today(),
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()

    # Mock the LLM service
    with patch('app.services.followup.build_followup_text') as mock_build:
        mock_build.return_value = "Good morning! Here are your tasks for today..."

        response = await client.post("/api/followup/run?slot=morning")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["slot"] == "morning"
        assert "Good morning" in data["message"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_followup_noon(client: AsyncClient):
    """Test POST /api/followup/run - Noon slot."""
    with patch('app.services.followup.build_followup_text') as mock_build:
        mock_build.return_value = "Noon update: Your afternoon tasks..."

        response = await client.post("/api/followup/run?slot=noon")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["slot"] == "noon"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_followup_evening(client: AsyncClient):
    """Test POST /api/followup/run - Evening slot."""
    with patch('app.services.followup.build_followup_text') as mock_build:
        mock_build.return_value = "Evening review: Here's what you accomplished..."

        response = await client.post("/api/followup/run?slot=evening")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["slot"] == "evening"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_followup_invalid_slot(client: AsyncClient):
    """Test POST /api/followup/run - Invalid slot."""
    response = await client.post("/api/followup/run?slot=invalid_slot")

    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_followup_empty_text(client: AsyncClient):
    """Test POST /api/followup/run - Empty text generation."""
    with patch('app.services.followup.build_followup_text') as mock_build:
        mock_build.return_value = None

        response = await client.post("/api/followup/run?slot=morning")

        assert response.status_code == 500


@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_followup_creates_message(client: AsyncClient, async_session):
    """Test POST /api/followup/run - Creates message in database."""
    from app.models.message import Message
    from sqlalchemy import select

    # Check initial message count
    result = await async_session.execute(select(Message))
    initial_count = len(result.scalars().all())

    with patch('app.services.followup.build_followup_text') as mock_build:
        mock_build.return_value = "Test followup message"

        response = await client.post("/api/followup/run?slot=morning")

        assert response.status_code == 200

    # Check that a message was created
    result = await async_session.execute(select(Message))
    messages = result.scalars().all()
    assert len(messages) == initial_count + 1
    assert messages[-1].role == "assistant"
    assert messages[-1].content == "Test followup message"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_followup_records_run(client: AsyncClient, async_session):
    """Test POST /api/followup/run - Records followup run in database."""
    from app.models.followup_run import FollowupRun
    from sqlalchemy import select

    # Check initial run count
    result = await async_session.execute(select(FollowupRun))
    initial_count = len(result.scalars().all())

    with patch('app.services.followup.build_followup_text') as mock_build:
        mock_build.return_value = "Test followup"

        response = await client.post("/api/followup/run?slot=morning")

        assert response.status_code == 200

    # Check that a run was recorded
    result = await async_session.execute(select(FollowupRun))
    runs = result.scalars().all()
    assert len(runs) == initial_count + 1
    assert runs[-1].slot == "morning"
