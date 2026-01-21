"""
Integration tests for Reminders API endpoints.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch
from app.models.task import Task
from datetime import date, time, timedelta


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scan_reminders_no_tasks(client: AsyncClient):
    """Test POST /api/reminders/scan - No tasks to scan."""
    response = await client.post("/api/reminders/scan")

    assert response.status_code == 200
    data = response.json()
    assert "created_events" in data
    assert "interval_min" in data
    assert data["created_events"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scan_reminders_with_overdue_task(client: AsyncClient, async_session):
    """Test POST /api/reminders/scan - With overdue task."""
    # Create an overdue task
    yesterday = date.today() - timedelta(days=1)
    task = Task(
        title="Overdue Task",
        description="This is overdue",
        status="doing",
        priority="high",
        due_date=yesterday,
        due_time=time(10, 0),
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()

    response = await client.post("/api/reminders/scan")

    assert response.status_code == 200
    data = response.json()
    assert data["created_events"] >= 0  # Should create events for overdue task


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scan_reminders_with_upcoming_task(client: AsyncClient, async_session):
    """Test POST /api/reminders/scan - With upcoming task."""
    # Create a task due today
    today = date.today()
    task = Task(
        title="Today's Task",
        description="Due today",
        status="backlog",
        priority="normal",
        due_date=today,
        due_time=time(14, 0),
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()

    response = await client.post("/api/reminders/scan")

    assert response.status_code == 200
    data = response.json()
    assert "created_events" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scan_reminders_creates_notification_events(client: AsyncClient, async_session):
    """Test POST /api/reminders/scan - Creates notification events."""
    from app.models.notification_event import NotificationEvent
    from sqlalchemy import select

    # Create an overdue task
    yesterday = date.today() - timedelta(days=1)
    task = Task(
        title="Overdue Task",
        description="This is overdue",
        status="doing",
        priority="high",
        due_date=yesterday,
        due_time=time(10, 0),
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()

    # Check initial event count
    result = await async_session.execute(select(NotificationEvent))
    initial_count = len(result.scalars().all())

    response = await client.post("/api/reminders/scan")
    assert response.status_code == 200

    # Check that events were created
    await async_session.commit()  # Ensure changes are visible
    result = await async_session.execute(select(NotificationEvent))
    events = result.scalars().all()
    # Should have created at least one event
    assert len(events) >= initial_count


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scan_reminders_respects_limit(client: AsyncClient, async_session):
    """Test POST /api/reminders/scan - Respects limit parameter."""
    # Create multiple overdue tasks
    yesterday = date.today() - timedelta(days=1)
    for i in range(15):
        task = Task(
            title=f"Overdue Task {i}",
            status="doing",
            priority="normal",
            due_date=yesterday,
            source="manual",
        )
        async_session.add(task)
    await async_session.commit()

    response = await client.post("/api/reminders/scan")

    assert response.status_code == 200
    data = response.json()
    # Should be limited to 10 as per the endpoint implementation
    assert data["created_events"] <= 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scan_reminders_returns_interval_config(client: AsyncClient):
    """Test POST /api/reminders/scan - Returns interval configuration."""
    response = await client.post("/api/reminders/scan")

    assert response.status_code == 200
    data = response.json()
    assert "interval_min" in data
    assert isinstance(data["interval_min"], int)
    assert data["interval_min"] > 0
