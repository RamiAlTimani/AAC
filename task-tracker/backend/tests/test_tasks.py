"""
Module 2 endpoint tests for the Task Tracker API.

Covers POST/GET/PATCH/DELETE on /tasks using the real in-memory storage layer
(reset around each test by the autouse fixture in conftest.py). TestClient only.
"""


# ---------------------------------------------------------------------------
# POST /tasks
# ---------------------------------------------------------------------------
def test_create_task_valid_returns_201_with_full_body(client):
    response = client.post(
        "/tasks",
        json={
            "title": "Write tests",
            "description": "Cover the tasks endpoints",
            "status": "ToDo",
            "priority": "High",
            "assignee": "rami",
        },
    )
    assert response.status_code == 201

    body = response.json()
    assert body["title"] == "Write tests"
    assert body["description"] == "Cover the tasks endpoints"
    assert body["status"] == "ToDo"
    assert body["priority"] == "High"
    assert body["assignee"] == "rami"

    # Server-assigned fields must be present.
    assert isinstance(body["id"], str) and body["id"]
    assert "created_at" in body
    assert "updated_at" in body


def test_create_task_missing_title_returns_422(client):
    response = client.post("/tasks", json={"description": "no title here"})
    assert response.status_code == 422


def test_create_task_blank_title_returns_422(client):
    response = client.post("/tasks", json={"title": "   "})
    assert response.status_code == 422


def test_create_task_invalid_priority_returns_422(client):
    response = client.post(
        "/tasks",
        json={"title": "Bad priority", "priority": "Urgent"},
    )
    assert response.status_code == 422


def test_create_task_unknown_field_returns_422(client):
    response = client.post(
        "/tasks",
        json={"title": "Has extra field", "color": "red"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /tasks
# ---------------------------------------------------------------------------
def test_list_tasks_empty_returns_200_and_empty_list(client):
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_filter_by_status_no_match_returns_200_and_empty_list(
    client, created_task
):
    # The fixture task defaults to status "ToDo"; filtering by "Done" matches none.
    response = client.get("/tasks", params={"status": "Done"})
    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_filter_by_priority_returns_only_matches(client):
    high = client.post(
        "/tasks", json={"title": "High one", "priority": "High"}
    ).json()
    client.post("/tasks", json={"title": "Low one", "priority": "Low"})

    response = client.get("/tasks", params={"priority": "High"})
    assert response.status_code == 200

    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == high["id"]
    assert body[0]["priority"] == "High"


# ---------------------------------------------------------------------------
# GET /tasks/{id}
# ---------------------------------------------------------------------------
def test_get_task_by_id_returns_task(client, created_task):
    response = client.get(f"/tasks/{created_task['id']}")
    assert response.status_code == 200

    body = response.json()
    assert body["id"] == created_task["id"]
    assert body["title"] == created_task["title"]


def test_get_task_by_id_not_found_returns_404_with_detail(client):
    response = client.get("/tasks/does-not-exist")
    assert response.status_code == 404
    assert "detail" in response.json()


# ---------------------------------------------------------------------------
# PATCH /tasks/{id}
# ---------------------------------------------------------------------------
def test_patch_partial_update_keeps_other_fields(client, created_task):
    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"description": "updated description"},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["description"] == "updated description"
    # Untouched fields are preserved.
    assert body["title"] == created_task["title"]
    assert body["status"] == created_task["status"]
    assert body["priority"] == created_task["priority"]


def test_patch_not_found_returns_404(client):
    response = client.patch(
        "/tasks/does-not-exist",
        json={"title": "new title"},
    )
    assert response.status_code == 404


def test_patch_valid_transition_todo_to_inprogress_returns_200(client, created_task):
    # Fixture task starts in "ToDo"; ToDo -> InProgress is a valid transition.
    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"status": "InProgress"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "InProgress"


def test_patch_invalid_transition_todo_to_done_returns_422(client, created_task):
    # ToDo -> Done is not an allowed transition.
    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"status": "Done"},
    )
    assert response.status_code == 422


def test_patch_same_status_returns_422(client, created_task):
    # Same -> same (ToDo -> ToDo) is invalid by construction.
    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"status": "ToDo"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /tasks/{id}
# ---------------------------------------------------------------------------
def test_delete_existing_returns_204_no_body(client, created_task):
    response = client.delete(f"/tasks/{created_task['id']}")
    assert response.status_code == 204
    assert response.content == b""


def test_delete_missing_returns_404(client):
    response = client.delete("/tasks/does-not-exist")
    assert response.status_code == 404
