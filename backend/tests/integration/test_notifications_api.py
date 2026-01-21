"""
Integration tests for Notifications API endpoints.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch
from app.models.notification_event import NotificationEvent
from app.models.task import Task
from datetime import date, time


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_notifications_empty(client: AsyncClient):
    """Test GET /api/notifications - Empty list."""
    response = await client.get("/api/notifications")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_notifications_with_events(client: AsyncClient, async_session):
    """Test GET /api/notifications - With notification events."""
    # Create a task first
    task = Task(
        title="Test Task",
        description="Test",
        status="doing",
        priority="high",
        due_date=date.today(),
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()
    await async_session.refresh(task)

    # Create notification events
    event1 = NotificationEvent(
        kind="deadline",
        task_id=task.id,
        stage="overdue",
        slot="morning",
        since=1,
        status="rendered",
        rendered_text="Task is overdue!",
    )
    event2 = NotificationEvent(
        kind="deadline",
        task_id=task.id,
        stage="today",
        slot="morning",
        since=0,
        status="rendered",
        rendered_text="Task is due today!",
    )

    async_session.add_all([event1, event2])
    await async_session.commit()

    # Get notifications
    response = await client.get("/api/notifications")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all("id" in event for event in data)
    assert all("kind" in event for event in data)
    assert all("status" in event for event in data)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_notifications_filter_by_status(client: AsyncClient, async_session):
    """Test GET /api/notifications - Filter by status."""
    # Create a task
    task = Task(
        title="Test Task",
        status="doing",
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()
    await async_session.refresh(task)

    # Create events with different statuses
    event1 = NotificationEvent(
        kind="deadline",
        task_id=task.id,
        stage="today",
        slot="morning",
        since=0,
        status="pending",
    )
    event2 = NotificationEvent(
        kind="deadline",
        task_id=task.id,
        stage="tomorrow",
        slot="morning",
        since=0,
        status="rendered",
        rendered_text="Reminder text",
    )

    async_session.add_all([event1, event2])
    await async_session.commit()

    # Get rendered notifications
    response = await client.get("/api/notifications?status=rendered")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "rendered"

    # Get pending notifications
    response = await client.get("/api/notifications?status=pending")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "pending"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_notifications_limit(client: AsyncClient, async_session):
    """Test GET /api/notifications - Limit parameter."""
    # Create a task
    task = Task(
        title="Test Task",
        status="doing",
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()
    await async_session.refresh(task)

    # Create multiple events
    for i in range(10):
        event = NotificationEvent(
            kind="deadline",
            task_id=task.id,
            stage="today",
            slot="morning",
            since=i,
            status="rendered",
            rendered_text=f"Event {i}",
        )
        async_session.add(event)
    await async_session.commit()

    # Get with limit
    response = await client.get("/api/notifications?limit=5")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_notifications_order(client: AsyncClient, async_session):
    """Test GET /api/notifications - Ordered by created_at desc."""
    # Create a task
    task = Task(
        title="Test Task",
        status="doing",
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()
    await async_session.refresh(task)

    # Create events
    event1 = NotificationEvent(
        kind="deadline",
        task_id=task.id,
        stage="today",
        slot="morning",
        since=0,
        status="rendered",
        rendered_text="First event",
    )
    async_session.add(event1)
    await async_session.commit()

    event2 = NotificationEvent(
        kind="deadline",
        task_id=task.id,
        stage="tomorrow",
        slot="noon",
        since=0,
        status="rendered",
        rendered_text="Second event",
    )
    async_session.add(event2)
    await async_session.commit()

    response = await client.get("/api/notifications")

    assert response.status_code == 200
    data = response.json()
    # Most recent should be first
    assert data[0]["rendered_text"] == "Second event"
    assert data[1]["rendered_text"] == "First event"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_render_notifications(client: AsyncClient, async_session):
    """Test POST /api/notifications/render - Render pending notifications."""
    # Create a task
    task = Task(
        title="Test Task",
        status="doing",
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()
    await async_session.refresh(task)

    # Create pending event
    event = NotificationEvent(
        kind="deadline",
        task_id=task.id,
        stage="today",
        slot="morning",
        since=0,
        status="pending",
    )
    async_session.add(event)
    await async_session.commit()

    # Mock the LLM service
    with patch('app.services.notification_render.call_llm_json') as mock_llm:
        mock_llm.return_value = {"text": "Your task is due today!"}

        response = await client.post("/api/notifications/render")

        assert response.status_code == 200
        data = response.json()
        assert "rendered" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_render_notifications_no_pending(client: AsyncClient):
    """Test POST /api/notifications/render - No pending notifications."""
    response = await client.post("/api/notifications/render")

    assert response.status_code == 200
    data = response.json()
    assert data["rendered"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_notifications_includes_all_fields(client: AsyncClient, async_session):
    """Test GET /api/notifications - Response includes all expected fields."""
    # Create a task
    task = Task(
        title="Test Task",
        status="doing",
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()
    await async_session.refresh(task)

    # Create event
    event = NotificationEvent(
        kind="deadline",
        task_id=task.id,
        stage="overdue",
        slot="morning",
        since=2,
        status="rendered",
        rendered_text="Test notification",
    )
    async_session.add(event)
    await async_session.commit()

    response = await client.get("/api/notifications")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

    event_data = data[0]
    assert "id" in event_data
    assert "kind" in event_data
    assert event_data["kind"] == "deadline"
    assert "task_id" in event_data
    assert "stage" in event_data
    assert event_data["stage"] == "overdue"
    assert "slot" in event_data
    assert event_data["slot"] == "morning"
    assert "since" in event_data
    assert event_data["since"] == 2
    assert "status" in event_data
    assert event_data["status"] == "rendered"
    assert "created_at" in event_data
    assert "rendered_at" in event_data
    assert "rendered_text" in event_data
    assert event_data["rendered_text"] == "Test notification"
