"""
Unit tests for followup service.
"""
import pytest
from datetime import date, timedelta
from app.services.followup import build_followup_text
from app.models.task import Task


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_followup_text_morning_empty(async_session):
    """Test morning followup with no tasks."""
    text = await build_followup_text(async_session, "morning")

    assert "[morning] フォロー" in text
    assert "今日の最優先を1つ選ぶ？" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_followup_text_morning_with_tasks(async_session):
    """Test morning followup with tasks."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Create overdue task
    task1 = Task(
        title="Overdue Task",
        status="doing",
        priority="high",
        due_date=yesterday,
        source="manual",
    )

    # Create task due today
    task2 = Task(
        title="Today Task",
        status="backlog",
        priority="normal",
        due_date=today,
        source="manual",
    )

    # Create doing task
    task3 = Task(
        title="In Progress",
        status="doing",
        priority="normal",
        source="manual",
    )

    async_session.add_all([task1, task2, task3])
    await async_session.commit()

    text = await build_followup_text(async_session, "morning")

    assert "[morning] フォロー" in text
    assert "期限切れ: 1件" in text
    assert "今日期限: 1件" in text
    assert "Doing: 2件" in text  # task1 and task3 are doing


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_followup_text_morning_skips_done(async_session):
    """Test morning followup skips done tasks."""
    today = date.today()

    # Create done task due today
    task1 = Task(
        title="Done Task",
        status="done",
        priority="normal",
        due_date=today,
        source="manual",
    )

    # Create active task due today
    task2 = Task(
        title="Active Task",
        status="backlog",
        priority="normal",
        due_date=today,
        source="manual",
    )

    async_session.add_all([task1, task2])
    await async_session.commit()

    text = await build_followup_text(async_session, "morning")

    # Should only count active task
    assert "今日期限: 1件" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_followup_text_noon_empty(async_session):
    """Test noon followup with no tasks."""
    text = await build_followup_text(async_session, "noon")

    assert "[noon] フォロー" in text
    assert "昼チェック" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_followup_text_noon_with_tasks(async_session):
    """Test noon followup with tasks."""
    today = date.today()

    task = Task(
        title="Today Task",
        status="backlog",
        priority="normal",
        due_date=today,
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()

    text = await build_followup_text(async_session, "noon")

    assert "[noon] フォロー" in text
    assert "昼チェック" in text
    assert "今日期限（未完了）: 1件" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_followup_text_evening_empty(async_session):
    """Test evening followup with no tasks."""
    text = await build_followup_text(async_session, "evening")

    assert "[evening] フォロー" in text
    assert "夕チェック" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_followup_text_evening_with_tasks(async_session):
    """Test evening followup with tasks."""
    today = date.today()

    task = Task(
        title="Today Task",
        status="backlog",
        priority="normal",
        due_date=today,
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()

    text = await build_followup_text(async_session, "evening")

    assert "[evening] フォロー" in text
    assert "夕チェック" in text
    assert "今日期限（未完了）: 1件" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_followup_text_multiple_overdue(async_session):
    """Test followup with multiple overdue tasks."""
    yesterday = date.today() - timedelta(days=1)
    two_days_ago = date.today() - timedelta(days=2)

    task1 = Task(
        title="Overdue 1",
        status="doing",
        priority="high",
        due_date=yesterday,
        source="manual",
    )

    task2 = Task(
        title="Overdue 2",
        status="backlog",
        priority="normal",
        due_date=two_days_ago,
        source="manual",
    )

    async_session.add_all([task1, task2])
    await async_session.commit()

    text = await build_followup_text(async_session, "morning")

    assert "期限切れ: 2件" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_followup_text_multiple_due_today(async_session):
    """Test followup with multiple tasks due today."""
    today = date.today()

    for i in range(3):
        task = Task(
            title=f"Today Task {i}",
            status="backlog",
            priority="normal",
            due_date=today,
            source="manual",
        )
        async_session.add(task)

    await async_session.commit()

    text = await build_followup_text(async_session, "morning")

    assert "今日期限: 3件" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_followup_text_multiple_doing(async_session):
    """Test followup with multiple doing tasks."""
    for i in range(4):
        task = Task(
            title=f"Doing Task {i}",
            status="doing",
            priority="normal",
            source="manual",
        )
        async_session.add(task)

    await async_session.commit()

    text = await build_followup_text(async_session, "morning")

    assert "Doing: 4件" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_followup_text_no_overdue_in_noon(async_session):
    """Test noon followup doesn't show overdue count."""
    yesterday = date.today() - timedelta(days=1)

    task = Task(
        title="Overdue Task",
        status="doing",
        priority="high",
        due_date=yesterday,
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()

    text = await build_followup_text(async_session, "noon")

    # Noon doesn't show overdue count
    assert "期限切れ" not in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_followup_text_no_overdue_in_evening(async_session):
    """Test evening followup doesn't show overdue count."""
    yesterday = date.today() - timedelta(days=1)

    task = Task(
        title="Overdue Task",
        status="doing",
        priority="high",
        due_date=yesterday,
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()

    text = await build_followup_text(async_session, "evening")

    # Evening doesn't show overdue count
    assert "期限切れ" not in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_followup_text_format(async_session):
    """Test followup text format is multi-line."""
    text = await build_followup_text(async_session, "morning")

    # Should be multi-line
    lines = text.split("\n")
    assert len(lines) > 1
    assert lines[0].startswith("[morning]")
