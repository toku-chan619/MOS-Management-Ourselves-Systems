"""
Test configuration and fixtures for MOS backend tests.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient
from app.main import app
from app.models.base import Base
from app.core.db import get_db
from app.core.config import settings

# Import all models so they are registered with Base.metadata
from app.models.task import Task
from app.models.project import Project
from app.models.message import Message
from app.models.draft import TaskDraft
from app.models.agent_run import AgentRun
from app.models.followup_run import FollowupRun
from app.models.notification_event import NotificationEvent
from app.models.notification_delivery import NotificationDelivery

# Test database URL (use shared in-memory SQLite for fast tests)
# Using file::memory:?cache=shared allows multiple connections to share the same in-memory database
TEST_DATABASE_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def async_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
async def client(async_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database session dependency override."""

    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for testing."""
    return {
        "tasks": [
            {
                "temp_id": "task-1",
                "title": "Test Task",
                "description": "Test Description",
                "status": "backlog",
                "priority": "normal",
                "due_date": None,
                "due_time": None,
                "confidence": 0.9,
                "parent_temp_id": None,
                "project_suggestion": "Test Project"
            }
        ]
    }


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "title": "Sample Task",
        "description": "Sample task description",
        "status": "backlog",
        "priority": "normal",
        "due_date": None,
        "due_time": None,
    }


@pytest.fixture
def sample_project_data():
    """Sample project data for testing."""
    return {
        "name": "Test Project",
        "is_archived": False,
    }


@pytest.fixture
def sample_message_data():
    """Sample message data for testing."""
    return {
        "content": "This is a test message"
    }
