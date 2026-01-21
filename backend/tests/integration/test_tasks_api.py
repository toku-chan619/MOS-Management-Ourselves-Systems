"""
Integration tests for Tasks API endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_task(client: AsyncClient, sample_task_data):
    """Test POST /api/tasks - Create a task."""
    response = await client.post("/api/tasks", json=sample_task_data)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == sample_task_data["title"]
    assert data["description"] == sample_task_data["description"]
    assert data["status"] == "backlog"
    assert data["priority"] == "normal"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_task(client: AsyncClient, sample_task_data):
    """Test GET /api/tasks/{task_id} - Get a task by ID."""
    # Create task first
    create_response = await client.post("/api/tasks", json=sample_task_data)
    task_id = create_response.json()["id"]

    # Get task
    response = await client.get(f"/api/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == sample_task_data["title"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_task_not_found(client: AsyncClient):
    """Test GET /api/tasks/{task_id} - Task not found."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/tasks/{fake_id}")

    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient, sample_task_data):
    """Test GET /api/tasks - List tasks."""
    # Create multiple tasks
    await client.post("/api/tasks", json={**sample_task_data, "title": "Task 1"})
    await client.post("/api/tasks", json={**sample_task_data, "title": "Task 2"})
    await client.post("/api/tasks", json={**sample_task_data, "title": "Task 3"})

    # List tasks
    response = await client.get("/api/tasks")

    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert "total" in data
    assert data["total"] == 3
    assert len(data["tasks"]) == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_tasks_with_filter(client: AsyncClient, sample_task_data):
    """Test GET /api/tasks - List tasks with status filter."""
    # Create tasks with different statuses
    await client.post("/api/tasks", json={**sample_task_data, "status": "backlog"})
    await client.post("/api/tasks", json={**sample_task_data, "status": "doing"})
    await client.post("/api/tasks", json={**sample_task_data, "status": "done"})

    # Filter by status=doing
    response = await client.get("/api/tasks?status=doing")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["tasks"][0]["status"] == "doing"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_tasks_pagination(client: AsyncClient, sample_task_data):
    """Test GET /api/tasks - List tasks with pagination."""
    # Create 5 tasks
    for i in range(5):
        await client.post("/api/tasks", json={**sample_task_data, "title": f"Task {i}"})

    # Get first page (limit=2)
    response = await client.get("/api/tasks?limit=2&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["tasks"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_task(client: AsyncClient, sample_task_data):
    """Test PUT /api/tasks/{task_id} - Update a task."""
    # Create task
    create_response = await client.post("/api/tasks", json=sample_task_data)
    task_id = create_response.json()["id"]

    # Update task
    update_data = {"title": "Updated Task", "status": "doing"}
    response = await client.put(f"/api/tasks/{task_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task"
    assert data["status"] == "doing"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_partial_update_task(client: AsyncClient, sample_task_data):
    """Test PATCH /api/tasks/{task_id} - Partially update a task."""
    # Create task
    create_response = await client.post("/api/tasks", json=sample_task_data)
    task_id = create_response.json()["id"]

    # Partial update (only status)
    update_data = {"status": "done"}
    response = await client.patch(f"/api/tasks/{task_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["title"] == sample_task_data["title"]  # Title unchanged


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_task(client: AsyncClient, sample_task_data):
    """Test DELETE /api/tasks/{task_id} - Delete a task."""
    # Create task
    create_response = await client.post("/api/tasks", json=sample_task_data)
    task_id = create_response.json()["id"]

    # Delete task
    response = await client.delete(f"/api/tasks/{task_id}")

    assert response.status_code == 204

    # Verify task is deleted
    get_response = await client.get(f"/api/tasks/{task_id}")
    assert get_response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_task_invalid_data(client: AsyncClient):
    """Test POST /api/tasks - Create task with invalid data."""
    invalid_data = {"title": ""}  # Empty title

    response = await client.post("/api/tasks", json=invalid_data)

    # Should fail validation (either 400 or 422)
    assert response.status_code in [400, 422]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_task_with_parent(client: AsyncClient, sample_task_data):
    """Test creating a task with a parent task."""
    # Create parent task
    parent_response = await client.post("/api/tasks", json={**sample_task_data, "title": "Parent Task"})
    parent_id = parent_response.json()["id"]

    # Create child task
    child_data = {**sample_task_data, "title": "Child Task", "parent_task_id": parent_id}
    response = await client.post("/api/tasks", json=child_data)

    assert response.status_code == 201
    data = response.json()
    assert data["parent_task_id"] == parent_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_task_tree(client: AsyncClient, sample_task_data):
    """Test GET /api/tasks/{task_id}/tree - Get task tree."""
    # Create parent task
    parent_response = await client.post("/api/tasks", json={**sample_task_data, "title": "Parent"})
    parent_id = parent_response.json()["id"]

    # Create child tasks
    await client.post("/api/tasks", json={**sample_task_data, "title": "Child 1", "parent_task_id": parent_id})
    await client.post("/api/tasks", json={**sample_task_data, "title": "Child 2", "parent_task_id": parent_id})

    # Get task tree
    response = await client.get(f"/api/tasks/{parent_id}/tree")

    assert response.status_code == 200
    tree = response.json()
    assert len(tree) == 3  # Parent + 2 children
