"""
Unit tests for database models.
"""
import pytest
from datetime import date, time
from sqlalchemy import select
from app.models.task import Task
from app.models.project import Project
from app.models.message import Message
from app.models.draft import TaskDraft
from app.models.followup_run import FollowupRun


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_project(async_session):
    """Test creating a project."""
    project = Project(name="Test Project", is_archived=False)
    async_session.add(project)
    await async_session.commit()
    await async_session.refresh(project)

    assert project.id is not None
    assert project.name == "Test Project"
    assert project.is_archived is False
    assert project.created_at is not None
    assert project.updated_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_task(async_session):
    """Test creating a task."""
    task = Task(
        title="Test Task",
        description="Test Description",
        status="backlog",
        priority="normal",
        due_date=date(2026, 12, 31),
        due_time=time(14, 30),
        source="manual",
    )
    async_session.add(task)
    await async_session.commit()
    await async_session.refresh(task)

    assert task.id is not None
    assert task.title == "Test Task"
    assert task.description == "Test Description"
    assert task.status == "backlog"
    assert task.priority == "normal"
    assert task.due_date == date(2026, 12, 31)
    assert task.due_time == time(14, 30)
    assert task.source == "manual"
    assert task.created_at is not None
    assert task.updated_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_task_with_project(async_session):
    """Test creating a task with a project."""
    # Create project
    project = Project(name="Work Project")
    async_session.add(project)
    await async_session.commit()
    await async_session.refresh(project)

    # Create task with project
    task = Task(
        title="Project Task",
        description="Task in project",
        project_id=project.id,
        source="chat",
    )
    async_session.add(task)
    await async_session.commit()
    await async_session.refresh(task)

    assert task.project_id == project.id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_task_hierarchy(async_session):
    """Test creating parent-child task relationship."""
    # Create parent task
    parent = Task(title="Parent Task", source="manual")
    async_session.add(parent)
    await async_session.commit()
    await async_session.refresh(parent)

    # Create child task
    child = Task(
        title="Child Task",
        parent_task_id=parent.id,
        source="manual",
    )
    async_session.add(child)
    await async_session.commit()
    await async_session.refresh(child)

    assert child.parent_task_id == parent.id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_message(async_session):
    """Test creating a message."""
    message = Message(role="user", content="Hello, world!")
    async_session.add(message)
    await async_session.commit()
    await async_session.refresh(message)

    assert message.id is not None
    assert message.role == "user"
    assert message.content == "Hello, world!"
    assert message.event_id is None
    assert message.created_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_task_draft(async_session):
    """Test creating a task draft."""
    # Create message first
    message = Message(role="user", content="Test message")
    async_session.add(message)
    await async_session.commit()
    await async_session.refresh(message)

    # Create draft
    draft = TaskDraft(
        message_id=message.id,
        status="proposed",
        draft_json={"tasks": []},
        confidence=0.8,
    )
    async_session.add(draft)
    await async_session.commit()
    await async_session.refresh(draft)

    assert draft.id is not None
    assert draft.message_id == message.id
    assert draft.status == "proposed"
    assert draft.confidence == 0.8
    assert draft.created_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_followup_run(async_session):
    """Test creating a followup run."""
    followup = FollowupRun(
        slot="morning",
        stats={"overdue": 2, "today": 5},
    )
    async_session.add(followup)
    await async_session.commit()
    await async_session.refresh(followup)

    assert followup.id is not None
    assert followup.slot == "morning"
    assert followup.stats == {"overdue": 2, "today": 5}
    assert followup.executed_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_project_archive(async_session):
    """Test archiving a project."""
    project = Project(name="Archive Test", is_archived=False)
    async_session.add(project)
    await async_session.commit()
    await async_session.refresh(project)

    # Archive project
    project.is_archived = True
    await async_session.commit()
    await async_session.refresh(project)

    assert project.is_archived is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_tasks_by_status(async_session):
    """Test querying tasks by status."""
    # Create tasks with different statuses
    task1 = Task(title="Backlog Task", status="backlog", source="manual")
    task2 = Task(title="Doing Task", status="doing", source="manual")
    task3 = Task(title="Done Task", status="done", source="manual")

    async_session.add_all([task1, task2, task3])
    await async_session.commit()

    # Query backlog tasks
    result = await async_session.execute(
        select(Task).where(Task.status == "backlog")
    )
    backlog_tasks = result.scalars().all()

    assert len(backlog_tasks) == 1
    assert backlog_tasks[0].title == "Backlog Task"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_projects_not_archived(async_session):
    """Test querying non-archived projects."""
    # Create projects
    project1 = Project(name="Active Project", is_archived=False)
    project2 = Project(name="Archived Project", is_archived=True)

    async_session.add_all([project1, project2])
    await async_session.commit()

    # Query non-archived projects
    result = await async_session.execute(
        select(Project).where(Project.is_archived == False)
    )
    active_projects = result.scalars().all()

    assert len(active_projects) == 1
    assert active_projects[0].name == "Active Project"
