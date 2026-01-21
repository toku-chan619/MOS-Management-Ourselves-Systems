"""
Integration tests for Projects API endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, sample_project_data):
    """Test POST /api/projects - Create a project."""
    response = await client.post("/api/projects", json=sample_project_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_project_data["name"]
    assert data["is_archived"] is False
    assert "id" in data
    assert "created_at" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_project_duplicate_name(client: AsyncClient, sample_project_data):
    """Test POST /api/projects - Duplicate project name."""
    # Create first project
    await client.post("/api/projects", json=sample_project_data)

    # Try to create second project with same name
    response = await client.post("/api/projects", json=sample_project_data)

    assert response.status_code == 409  # Conflict


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_project(client: AsyncClient, sample_project_data):
    """Test GET /api/projects/{project_id} - Get a project by ID."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project_data)
    project_id = create_response.json()["id"]

    # Get project
    response = await client.get(f"/api/projects/{project_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == sample_project_data["name"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, sample_project_data):
    """Test GET /api/projects - List projects."""
    # Create multiple projects
    await client.post("/api/projects", json={**sample_project_data, "name": "Project 1"})
    await client.post("/api/projects", json={**sample_project_data, "name": "Project 2"})
    await client.post("/api/projects", json={**sample_project_data, "name": "Project 3"})

    # List projects
    response = await client.get("/api/projects")

    assert response.status_code == 200
    data = response.json()
    assert "projects" in data
    assert "total" in data
    assert data["total"] == 3
    assert len(data["projects"]) == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_projects_filter_archived(client: AsyncClient, sample_project_data):
    """Test GET /api/projects - Filter by archived status."""
    # Create active and archived projects
    await client.post("/api/projects", json={**sample_project_data, "name": "Active", "is_archived": False})
    await client.post("/api/projects", json={**sample_project_data, "name": "Archived", "is_archived": True})

    # Filter for non-archived projects
    response = await client.get("/api/projects?is_archived=false")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["projects"][0]["name"] == "Active"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, sample_project_data):
    """Test PUT /api/projects/{project_id} - Update a project."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project_data)
    project_id = create_response.json()["id"]

    # Update project
    update_data = {"name": "Updated Project Name"}
    response = await client.put(f"/api/projects/{project_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Project Name"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_project_archive(client: AsyncClient, sample_project_data):
    """Test DELETE /api/projects/{project_id} - Archive a project (soft delete)."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project_data)
    project_id = create_response.json()["id"]

    # Delete (archive) project
    response = await client.delete(f"/api/projects/{project_id}")

    assert response.status_code == 204

    # Verify project is archived
    get_response = await client.get(f"/api/projects/{project_id}")
    assert get_response.status_code == 200
    assert get_response.json()["is_archived"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_project_force(client: AsyncClient, sample_project_data):
    """Test DELETE /api/projects/{project_id}?force=true - Hard delete."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project_data)
    project_id = create_response.json()["id"]

    # Force delete project
    response = await client.delete(f"/api/projects/{project_id}?force=true")

    assert response.status_code == 204

    # Verify project is actually deleted
    get_response = await client.get(f"/api/projects/{project_id}")
    assert get_response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_project_tasks(client: AsyncClient, sample_project_data, sample_task_data):
    """Test GET /api/projects/{project_id}/tasks - Get tasks in a project."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project_data)
    project_id = create_response.json()["id"]

    # Create tasks in project
    await client.post("/api/tasks", json={**sample_task_data, "project_id": project_id, "title": "Task 1"})
    await client.post("/api/tasks", json={**sample_task_data, "project_id": project_id, "title": "Task 2"})

    # Get project tasks
    response = await client.get(f"/api/projects/{project_id}/tasks")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["tasks"]) == 2
    assert all(t["project_id"] == project_id for t in data["tasks"])
