"""
Integration tests for Chat API endpoints.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_message(client: AsyncClient, sample_message_data):
    """Test POST /api/chat/messages - Post a message."""
    # Mock Celery task
    with patch('app.routers.chat.extract_and_store_draft') as mock_task:
        mock_task.delay = AsyncMock()

        response = await client.post("/api/chat/messages", json=sample_message_data)

        assert response.status_code == 201
        data = response.json()
        assert "message_id" in data
        assert data["status"] == "queued"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_empty_message(client: AsyncClient):
    """Test POST /api/chat/messages - Empty message."""
    response = await client.post("/api/chat/messages", json={"content": ""})

    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_messages(client: AsyncClient, sample_message_data):
    """Test GET /api/chat/messages - Get message history."""
    # Post some messages
    with patch('app.routers.chat.extract_and_store_draft.delay'):
        await client.post("/api/chat/messages", json={"content": "Message 1"})
        await client.post("/api/chat/messages", json={"content": "Message 2"})

    # Get messages
    response = await client.get("/api/chat/messages")

    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert "total" in data
    assert data["total"] == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_messages_with_role_filter(client: AsyncClient, sample_message_data):
    """Test GET /api/chat/messages - Filter by role."""
    # Get messages with role filter
    response = await client.get("/api/chat/messages?role=user")

    assert response.status_code == 200
    data = response.json()
    assert all(m["role"] == "user" for m in data["messages"])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_message_by_id(client: AsyncClient, sample_message_data):
    """Test GET /api/chat/messages/{message_id} - Get a specific message."""
    # Post message
    with patch('app.routers.chat.extract_and_store_draft.delay'):
        post_response = await client.post("/api/chat/messages", json=sample_message_data)
        message_id = post_response.json()["message_id"]

    # Get message by ID
    response = await client.get(f"/api/chat/messages/{message_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == message_id
    assert data["content"] == sample_message_data["content"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_messages_pagination(client: AsyncClient):
    """Test GET /api/chat/messages - Pagination."""
    # Post multiple messages
    with patch('app.routers.chat.extract_and_store_draft.delay'):
        for i in range(5):
            await client.post("/api/chat/messages", json={"content": f"Message {i}"})

    # Get first page
    response = await client.get("/api/chat/messages?limit=2&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["messages"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0
