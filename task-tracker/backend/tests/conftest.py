"""
Shared pytest fixtures for the Task Tracker API tests.

Uses the real in-memory storage layer (no mocking) and resets it around every
test so each test starts from a clean, isolated state.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import storage


@pytest.fixture(autouse=True)
def _reset_storage():
    """Clear stored tasks before and after each test for isolation."""
    storage._reset()
    yield
    storage._reset()


@pytest.fixture
def client():
    """A TestClient bound to the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def created_task(client):
    """Create a task via the API and return its JSON representation."""
    response = client.post("/tasks", json={"title": "fixture task"})
    assert response.status_code == 201
    return response.json()
