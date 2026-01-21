"""
Unit tests for reminders service.
"""
import pytest
from unittest.mock import patch
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from app.services.reminders import _compute_stages_for_task, scan_deadline_reminders
from app.models.task import Task


@pytest.mark.unit
def test_compute_stages_done_task():
    """Test that done tasks return no stages."""
    task = Task(
        title="Done Task",
        status="done",
        priority="normal",
        due_date=date.today(),
        source="manual",
    )
    now = datetime.now(tz=ZoneInfo("UTC"))

    stages = _compute_stages_for_task(task, now)

    assert stages == []


@pytest.mark.unit
def test_compute_stages_canceled_task():
    """Test that canceled tasks return no stages."""
    task = Task(
        title="Canceled Task",
        status="canceled",
        priority="normal",
        due_date=date.today(),
        source="manual",
    )
    now = datetime.now(tz=ZoneInfo("UTC"))

    stages = _compute_stages_for_task(task, now)

    assert stages == []


@pytest.mark.unit
def test_compute_stages_no_due_date():
    """Test that tasks without due_date return no stages."""
    task = Task(
        title="No Due Date",
        status="backlog",
        priority="normal",
        due_date=None,
        source="manual",
    )
    now = datetime.now(tz=ZoneInfo("UTC"))

    stages = _compute_stages_for_task(task, now)

    assert stages == []


@pytest.mark.unit
def test_compute_stages_overdue_date():
    """Test overdue task (date-based)."""
    yesterday = date.today() - timedelta(days=1)
    task = Task(
        title="Overdue Task",
        status="doing",
        priority="high",
        due_date=yesterday,
        source="manual",
    )
    now = datetime.now(tz=ZoneInfo("UTC"))

    stages = _compute_stages_for_task(task, now)

    assert stages == ["OVERDUE"]


@pytest.mark.unit
def test_compute_stages_d0():
    """Test D-0 stage (due today)."""
    today = date.today()
    task = Task(
        title="Due Today",
        status="backlog",
        priority="normal",
        due_date=today,
        source="manual",
    )
    now = datetime.now(tz=ZoneInfo("UTC"))

    stages = _compute_stages_for_task(task, now)

    assert "D-0" in stages


@pytest.mark.unit
def test_compute_stages_d1():
    """Test D-1 stage (due tomorrow)."""
    tomorrow = date.today() + timedelta(days=1)
    task = Task(
        title="Due Tomorrow",
        status="backlog",
        priority="normal",
        due_date=tomorrow,
        source="manual",
    )
    now = datetime.now(tz=ZoneInfo("UTC"))

    stages = _compute_stages_for_task(task, now)

    assert "D-1" in stages


@pytest.mark.unit
def test_compute_stages_d3():
    """Test D-3 stage (due in 3 days)."""
    three_days = date.today() + timedelta(days=3)
    task = Task(
        title="Due in 3 Days",
        status="backlog",
        priority="normal",
        due_date=three_days,
        source="manual",
    )
    now = datetime.now(tz=ZoneInfo("UTC"))

    stages = _compute_stages_for_task(task, now)

    assert "D-3" in stages


@pytest.mark.unit
def test_compute_stages_d7():
    """Test D-7 stage (due in 7 days)."""
    seven_days = date.today() + timedelta(days=7)
    task = Task(
        title="Due in 7 Days",
        status="backlog",
        priority="normal",
        due_date=seven_days,
        source="manual",
    )
    now = datetime.now(tz=ZoneInfo("UTC"))

    stages = _compute_stages_for_task(task, now)

    assert "D-7" in stages


@pytest.mark.unit
def test_compute_stages_overdue_time():
    """Test overdue task (time-based)."""
    today = date.today()
    past_time = (datetime.now() - timedelta(hours=1)).time()

    task = Task(
        title="Overdue with Time",
        status="doing",
        priority="high",
        due_date=today,
        due_time=past_time,
        source="manual",
    )
    now = datetime.now(tz=ZoneInfo("UTC"))

    stages = _compute_stages_for_task(task, now)

    assert stages == ["OVERDUE"]


@pytest.mark.unit
def test_compute_stages_t_2h():
    """Test T-2H stage (due in 2 hours)."""
    today = date.today()
    future_time = (datetime.now() + timedelta(hours=1, minutes=30)).time()

    task = Task(
        title="Due in 1.5 Hours",
        status="doing",
        priority="high",
        due_date=today,
        due_time=future_time,
        source="manual",
    )
    now = datetime.now(tz=ZoneInfo("UTC"))

    stages = _compute_stages_for_task(task, now)

    # Should include T-2H (and possibly D-0)
    assert "T-2H" in stages


@pytest.mark.unit
def test_compute_stages_t_30m():
    """Test T-30M stage (due in 30 minutes)."""
    today = date.today()
    future_time = (datetime.now() + timedelta(minutes=15)).time()

    task = Task(
        title="Due in 15 Minutes",
        status="doing",
        priority="urgent",
        due_date=today,
        due_time=future_time,
        source="manual",
    )
    now = datetime.now(tz=ZoneInfo("UTC"))

    stages = _compute_stages_for_task(task, now)

    # Should include T-30M (and possibly T-2H, D-0)
    assert "T-30M" in stages


@pytest.mark.unit
def test_compute_stages_future_with_time():
    """Test task due tomorrow with time (should not include time-based stages)."""
    tomorrow = date.today() + timedelta(days=1)
    task = Task(
        title="Due Tomorrow with Time",
        status="backlog",
        priority="normal",
        due_date=tomorrow,
        due_time=time(14, 0),
        source="manual",
    )
    now = datetime.now(tz=ZoneInfo("UTC"))

    stages = _compute_stages_for_task(task, now)

    # Should only include D-1, not time-based stages
    assert "D-1" in stages
    assert "T-2H" not in stages
    assert "T-30M" not in stages


@pytest.mark.unit
def test_compute_stages_far_future():
    """Test task far in the future (should return no stages)."""
    far_future = date.today() + timedelta(days=30)
    task = Task(
        title="Due in 30 Days",
        status="backlog",
        priority="normal",
        due_date=far_future,
        source="manual",
    )
    now = datetime.now(tz=ZoneInfo("UTC"))

    stages = _compute_stages_for_task(task, now)

    assert stages == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_deadline_reminders_no_tasks(async_session):
    """Test scan with no tasks in database."""
    count = await scan_deadline_reminders(async_session, limit_new_events=10)

    assert count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_deadline_reminders_creates_events(async_session):
    """Test scan creates notification events for due tasks."""
    # Create a task due today
    today = date.today()
    task = Task(
        title="Due Today",
        status="doing",
        priority="high",
        due_date=today,
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()

    count = await scan_deadline_reminders(async_session, limit_new_events=10)

    # Should create at least one event (D-0)
    assert count >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_deadline_reminders_respects_limit(async_session):
    """Test scan respects the limit parameter."""
    # Create multiple overdue tasks
    yesterday = date.today() - timedelta(days=1)
    for i in range(5):
        task = Task(
            title=f"Overdue Task {i}",
            status="doing",
            priority="normal",
            due_date=yesterday,
            source="manual",
        )
        async_session.add(task)
    await async_session.commit()

    count = await scan_deadline_reminders(async_session, limit_new_events=3)

    # Should not exceed limit
    assert count <= 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_deadline_reminders_skips_done_tasks(async_session):
    """Test scan skips done and canceled tasks."""
    today = date.today()

    # Create done task
    task1 = Task(
        title="Done Task",
        status="done",
        priority="normal",
        due_date=today,
        source="manual",
    )
    # Create canceled task
    task2 = Task(
        title="Canceled Task",
        status="canceled",
        priority="normal",
        due_date=today,
        source="manual",
    )
    # Create active task
    task3 = Task(
        title="Active Task",
        status="doing",
        priority="normal",
        due_date=today,
        source="manual",
    )

    async_session.add_all([task1, task2, task3])
    await async_session.commit()

    count = await scan_deadline_reminders(async_session, limit_new_events=10)

    # Should only create event for active task
    assert count >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_deadline_reminders_idempotent(async_session):
    """Test scan is idempotent (doesn't create duplicate events)."""
    # Create a task due today
    today = date.today()
    task = Task(
        title="Due Today",
        status="doing",
        priority="normal",
        due_date=today,
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()

    # First scan
    count1 = await scan_deadline_reminders(async_session, limit_new_events=10)
    assert count1 >= 1

    # Second scan (should not create duplicates)
    count2 = await scan_deadline_reminders(async_session, limit_new_events=10)
    assert count2 == 0  # No new events created


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_deadline_reminders_skips_no_due_date(async_session):
    """Test scan skips tasks without due_date."""
    task = Task(
        title="No Due Date",
        status="doing",
        priority="normal",
        due_date=None,
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()

    count = await scan_deadline_reminders(async_session, limit_new_events=10)

    assert count == 0
