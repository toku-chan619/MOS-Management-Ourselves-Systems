"""
Integration tests for Drafts API endpoints.
"""
import pytest
from httpx import AsyncClient
from app.models.draft import TaskDraft
from app.models.message import Message


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_drafts_empty(client: AsyncClient):
    """Test GET /api/task-drafts - Empty list."""
    response = await client.get("/api/task-drafts")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_drafts_with_status_filter(client: AsyncClient, async_session):
    """Test GET /api/task-drafts - Filter by status."""
    # Create a message first
    message = Message(role="user", content="Test message")
    async_session.add(message)
    await async_session.commit()
    await async_session.refresh(message)

    # Create drafts with different statuses
    draft1 = TaskDraft(
        message_id=message.id,
        status="proposed",
        draft_json={"tasks": [{"temp_id": "t1", "title": "Task 1"}]},
        confidence=0.9,
    )
    draft2 = TaskDraft(
        message_id=message.id,
        status="accepted",
        draft_json={"tasks": [{"temp_id": "t2", "title": "Task 2"}]},
        confidence=0.8,
    )

    async_session.add_all([draft1, draft2])
    await async_session.commit()

    # Get proposed drafts
    response = await client.get("/api/task-drafts?status=proposed")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "proposed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_accept_draft_success(client: AsyncClient, async_session):
    """Test POST /api/task-drafts/{draft_id}/accept - Success."""
    # Create message
    message = Message(role="user", content="Test message")
    async_session.add(message)
    await async_session.commit()
    await async_session.refresh(message)

    # Create draft with valid task data
    draft = TaskDraft(
        message_id=message.id,
        status="proposed",
        draft_json={
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
        },
        confidence=0.9,
    )
    async_session.add(draft)
    await async_session.commit()
    await async_session.refresh(draft)

    # Accept draft
    response = await client.post(f"/api/task-drafts/{draft.id}/accept")

    assert response.status_code == 200
    data = response.json()
    assert "created_task_ids" in data
    assert len(data["created_task_ids"]) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_accept_draft_not_found(client: AsyncClient):
    """Test POST /api/task-drafts/{draft_id}/accept - Draft not found."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = await client.post(f"/api/task-drafts/{fake_uuid}/accept")

    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_accept_draft_invalid_uuid(client: AsyncClient):
    """Test POST /api/task-drafts/{draft_id}/accept - Invalid UUID."""
    response = await client.post("/api/task-drafts/invalid-uuid/accept")

    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_accept_draft_with_hierarchy(client: AsyncClient, async_session):
    """Test POST /api/task-drafts/{draft_id}/accept - With task hierarchy."""
    # Create message
    message = Message(role="user", content="Test message")
    async_session.add(message)
    await async_session.commit()
    await async_session.refresh(message)

    # Create draft with parent-child tasks
    draft = TaskDraft(
        message_id=message.id,
        status="proposed",
        draft_json={
            "tasks": [
                {
                    "temp_id": "parent-1",
                    "title": "Parent Task",
                    "description": "Parent",
                    "status": "backlog",
                    "priority": "high",
                    "due_date": None,
                    "due_time": None,
                    "confidence": 0.9,
                    "parent_temp_id": None,
                    "project_suggestion": None
                },
                {
                    "temp_id": "child-1",
                    "title": "Child Task",
                    "description": "Child",
                    "status": "backlog",
                    "priority": "normal",
                    "due_date": None,
                    "due_time": None,
                    "confidence": 0.8,
                    "parent_temp_id": "parent-1",
                    "project_suggestion": None
                }
            ]
        },
        confidence=0.85,
    )
    async_session.add(draft)
    await async_session.commit()
    await async_session.refresh(draft)

    # Accept draft
    response = await client.post(f"/api/task-drafts/{draft.id}/accept")

    assert response.status_code == 200
    data = response.json()
    assert len(data["created_task_ids"]) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_accept_draft_invalid_parent_reference(client: AsyncClient, async_session):
    """Test POST /api/task-drafts/{draft_id}/accept - Invalid parent reference."""
    # Create message
    message = Message(role="user", content="Test message")
    async_session.add(message)
    await async_session.commit()
    await async_session.refresh(message)

    # Create draft with invalid parent reference
    draft = TaskDraft(
        message_id=message.id,
        status="proposed",
        draft_json={
            "tasks": [
                {
                    "temp_id": "child-1",
                    "title": "Child Task",
                    "description": "Child",
                    "status": "backlog",
                    "priority": "normal",
                    "due_date": None,
                    "due_time": None,
                    "confidence": 0.8,
                    "parent_temp_id": "nonexistent-parent",
                    "project_suggestion": None
                }
            ]
        },
        confidence=0.8,
    )
    async_session.add(draft)
    await async_session.commit()
    await async_session.refresh(draft)

    # Accept draft should fail
    response = await client.post(f"/api/task-drafts/{draft.id}/accept")

    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reject_draft_success(client: AsyncClient, async_session):
    """Test POST /api/task-drafts/{draft_id}/reject - Success."""
    # Create message
    message = Message(role="user", content="Test message")
    async_session.add(message)
    await async_session.commit()
    await async_session.refresh(message)

    # Create draft
    draft = TaskDraft(
        message_id=message.id,
        status="proposed",
        draft_json={"tasks": []},
        confidence=0.5,
    )
    async_session.add(draft)
    await async_session.commit()
    await async_session.refresh(draft)

    # Reject draft
    response = await client.post(f"/api/task-drafts/{draft.id}/reject")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["draft_id"] == str(draft.id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reject_draft_not_found(client: AsyncClient):
    """Test POST /api/task-drafts/{draft_id}/reject - Draft not found."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = await client.post(f"/api/task-drafts/{fake_uuid}/reject")

    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reject_draft_already_accepted(client: AsyncClient, async_session):
    """Test POST /api/task-drafts/{draft_id}/reject - Already accepted draft."""
    # Create message
    message = Message(role="user", content="Test message")
    async_session.add(message)
    await async_session.commit()
    await async_session.refresh(message)

    # Create draft with accepted status
    draft = TaskDraft(
        message_id=message.id,
        status="accepted",
        draft_json={"tasks": []},
        confidence=0.9,
    )
    async_session.add(draft)
    await async_session.commit()
    await async_session.refresh(draft)

    # Try to reject
    response = await client.post(f"/api/task-drafts/{draft.id}/reject")

    assert response.status_code == 400
