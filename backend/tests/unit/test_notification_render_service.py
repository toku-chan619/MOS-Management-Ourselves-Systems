"""
Unit tests for notification_render service.
"""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime
from app.services.notification_render import _render_event_text, render_and_project_in_app
from app.models.notification_event import NotificationEvent
from app.models.task import Task
from app.core.exceptions import LLMAPIError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_event_text_deadline_reminder():
    """Test rendering deadline reminder event."""
    event = NotificationEvent(
        kind="task_deadline_reminder",
        stage="D-0",
        status="created",
        payload={
            "kind": "task_deadline_reminder",
            "stage": "D-0",
            "task": {
                "id": "task-123",
                "title": "Complete report",
                "status": "doing",
                "priority": "high"
            }
        }
    )

    with patch('app.services.notification_render.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {"text": "レポートを本日中に完成させましょう。"}

        text = await _render_event_text(event)

        assert text == "レポートを本日中に完成させましょう。"
        mock_llm.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_event_text_followup_summary():
    """Test rendering followup summary event."""
    event = NotificationEvent(
        kind="followup_summary",
        slot="morning",
        status="created",
        payload={
            "kind": "followup_summary",
            "slot": "morning",
            "stats": {"overdue": 2, "today": 3}
        }
    )

    with patch('app.services.notification_render.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {"text": "おはようございます。期限切れ2件、本日期限3件です。"}

        text = await _render_event_text(event)

        assert text == "おはようございます。期限切れ2件、本日期限3件です。"
        mock_llm.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_event_text_empty_text():
    """Test rendering with empty text response."""
    event = NotificationEvent(
        kind="task_deadline_reminder",
        stage="D-0",
        status="created",
        payload={"task": {}}
    )

    with patch('app.services.notification_render.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {"text": ""}

        with pytest.raises(ValueError, match="Empty text in LLM response"):
            await _render_event_text(event)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_event_text_unknown_kind():
    """Test rendering with unknown event kind."""
    event = NotificationEvent(
        kind="unknown_kind",
        status="created",
        payload={}
    )

    with pytest.raises(ValueError, match="Unknown event kind"):
        await _render_event_text(event)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_event_text_llm_error():
    """Test rendering with LLM API error."""
    event = NotificationEvent(
        kind="task_deadline_reminder",
        stage="D-0",
        status="created",
        payload={"task": {}}
    )

    with patch('app.services.notification_render.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = LLMAPIError("API error")

        with pytest.raises(LLMAPIError):
            await _render_event_text(event)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_and_project_no_events(async_session):
    """Test render_and_project_in_app with no events."""
    count = await render_and_project_in_app(async_session, batch_size=10)

    assert count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_and_project_success(async_session):
    """Test render_and_project_in_app successfully processes events."""
    # Create a task
    task = Task(
        title="Test Task",
        status="doing",
        priority="high",
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()
    await async_session.refresh(task)

    # Create notification event
    event = NotificationEvent(
        kind="task_deadline_reminder",
        task_id=task.id,
        stage="D-0",
        status="created",
        payload={
            "kind": "task_deadline_reminder",
            "stage": "D-0",
            "task": {
                "id": str(task.id),
                "title": "Test Task"
            }
        }
    )
    async_session.add(event)
    await async_session.commit()

    # Mock LLM response
    with patch('app.services.notification_render.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {"text": "テストタスクの期限が近づいています。"}

        count = await render_and_project_in_app(async_session, batch_size=10)

        assert count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_and_project_creates_message(async_session):
    """Test render_and_project_in_app creates message."""
    from app.models.message import Message
    from sqlalchemy import select

    # Create a task
    task = Task(
        title="Test Task",
        status="doing",
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()
    await async_session.refresh(task)

    # Create notification event
    event = NotificationEvent(
        kind="task_deadline_reminder",
        task_id=task.id,
        stage="D-0",
        status="created",
        payload={"task": {"title": "Test"}}
    )
    async_session.add(event)
    await async_session.commit()

    # Check initial message count
    result = await async_session.execute(select(Message))
    initial_count = len(result.scalars().all())

    # Mock LLM response
    with patch('app.services.notification_render.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {"text": "通知メッセージ"}

        await render_and_project_in_app(async_session, batch_size=10)

    # Check that a message was created
    result = await async_session.execute(select(Message))
    messages = result.scalars().all()
    assert len(messages) == initial_count + 1
    assert messages[-1].role == "assistant"
    assert messages[-1].content == "通知メッセージ"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_and_project_creates_delivery(async_session):
    """Test render_and_project_in_app creates delivery record."""
    from app.models.notification_delivery import NotificationDelivery
    from sqlalchemy import select

    # Create a task
    task = Task(
        title="Test Task",
        status="doing",
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()
    await async_session.refresh(task)

    # Create notification event
    event = NotificationEvent(
        kind="task_deadline_reminder",
        task_id=task.id,
        stage="D-0",
        status="created",
        payload={"task": {"title": "Test"}}
    )
    async_session.add(event)
    await async_session.commit()

    # Mock LLM response
    with patch('app.services.notification_render.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {"text": "通知"}

        await render_and_project_in_app(async_session, batch_size=10)

    # Check that a delivery was created
    result = await async_session.execute(select(NotificationDelivery))
    deliveries = result.scalars().all()
    assert len(deliveries) == 1
    assert deliveries[0].channel == "in_app"
    assert deliveries[0].status == "sent"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_and_project_updates_event_status(async_session):
    """Test render_and_project_in_app updates event status."""
    from sqlalchemy import select

    # Create a task
    task = Task(
        title="Test Task",
        status="doing",
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()
    await async_session.refresh(task)

    # Create notification event
    event = NotificationEvent(
        kind="task_deadline_reminder",
        task_id=task.id,
        stage="D-0",
        status="created",
        payload={"task": {"title": "Test"}}
    )
    async_session.add(event)
    await async_session.commit()
    event_id = event.id

    # Mock LLM response
    with patch('app.services.notification_render.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {"text": "レンダリング完了"}

        await render_and_project_in_app(async_session, batch_size=10)

    # Check event was updated
    result = await async_session.execute(
        select(NotificationEvent).where(NotificationEvent.id == event_id)
    )
    updated_event = result.scalars().first()
    assert updated_event.status == "rendered"
    assert updated_event.rendered_text == "レンダリング完了"
    assert updated_event.rendered_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_and_project_batch_size(async_session):
    """Test render_and_project_in_app respects batch_size."""
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
    for i in range(5):
        event = NotificationEvent(
            kind="task_deadline_reminder",
            task_id=task.id,
            stage="D-0",
            status="created",
            payload={"task": {"title": f"Task {i}"}}
        )
        async_session.add(event)
    await async_session.commit()

    # Mock LLM response
    with patch('app.services.notification_render.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {"text": "通知"}

        # Process only 3 events
        count = await render_and_project_in_app(async_session, batch_size=3)

        assert count == 3
        assert mock_llm.call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_and_project_handles_llm_error(async_session):
    """Test render_and_project_in_app handles LLM errors gracefully."""
    from sqlalchemy import select

    # Create a task
    task = Task(
        title="Test Task",
        status="doing",
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()
    await async_session.refresh(task)

    # Create notification event
    event = NotificationEvent(
        kind="task_deadline_reminder",
        task_id=task.id,
        stage="D-0",
        status="created",
        payload={"task": {"title": "Test"}}
    )
    async_session.add(event)
    await async_session.commit()
    event_id = event.id

    # Mock LLM to raise error
    with patch('app.services.notification_render.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = LLMAPIError("API error")

        count = await render_and_project_in_app(async_session, batch_size=10)

        # Should handle error and return 0 processed
        assert count == 0

    # Check event was marked as failed
    result = await async_session.execute(
        select(NotificationEvent).where(NotificationEvent.id == event_id)
    )
    failed_event = result.scalars().first()
    assert failed_event.status == "failed"
    assert "LLM error" in failed_event.rendered_text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_and_project_continues_after_error(async_session):
    """Test render_and_project_in_app continues processing after error."""
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
    event1 = NotificationEvent(
        kind="task_deadline_reminder",
        task_id=task.id,
        stage="D-0",
        status="created",
        payload={"task": {"title": "Task 1"}}
    )
    event2 = NotificationEvent(
        kind="task_deadline_reminder",
        task_id=task.id,
        stage="D-1",
        status="created",
        payload={"task": {"title": "Task 2"}}
    )
    async_session.add_all([event1, event2])
    await async_session.commit()

    # Mock LLM: first fails, second succeeds
    with patch('app.services.notification_render.call_llm_json', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = [
            LLMAPIError("First error"),
            {"text": "成功"}
        ]

        count = await render_and_project_in_app(async_session, batch_size=10)

        # Should have processed 1 successfully (second event)
        assert count == 1
        assert mock_llm.call_count == 2
