"""
Application entry point.

Creates the FastAPI app instance and registers routers. Run it with:
    uvicorn app.main:app --reload
or directly with:
    python -m app.main
"""
import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.business_rules import validate_status_transition
from app.core.config import PORT
from app.models import TaskCreate, TaskStatus, TaskPriority, TaskResponse, TaskUpdate
from app.routers import health
from app import storage

# The FastAPI application instance. Uvicorn looks for this object
# when started as `uvicorn app.main:app`.
app = FastAPI(
    title="Task Tracker API",
    description="REST API backend for the Task Tracker learning project.",
    version="0.1.0",
)

# Allow the local frontend (served by Live Server) to read API responses from
# the browser. Scoped to the known dev origin only — not a wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the health-check router.
app.include_router(health.router)


@app.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["tasks"],
)
def create_task(payload: TaskCreate) -> TaskResponse:
    """Create a new task.

    Validation (required/blank/overlong title, invalid status or priority,
    and unknown fields) is handled entirely by the TaskCreate Pydantic model,
    which returns HTTP 422 automatically on failure. The storage layer assigns
    the id and timestamps.
    """
    return storage.add_task(payload)


@app.get(
    "/tasks",
    response_model=list[TaskResponse],
    tags=["tasks"],
)
def list_tasks(
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
) -> list[TaskResponse]:
    """List tasks, optionally filtered by status and/or priority.

    An empty result is a valid response and returns 200 with an empty list.
    Invalid enum values in the query string are rejected with 422 by FastAPI.
    """
    return storage.get_all_tasks(status=status, priority=priority)


@app.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    tags=["tasks"],
)
def get_task(task_id: str) -> TaskResponse:
    """Fetch a single task by id, or 404 if it does not exist."""
    task = storage.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task with id {task_id} not found",
        )
    return task


@app.patch(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    tags=["tasks"],
)
def update_task(task_id: str, payload: TaskUpdate) -> TaskResponse:
    """Apply a partial update to a task, or 404 if it does not exist.

    Body validation (blank/overlong title, invalid status or priority,
    unknown fields) is handled by the TaskUpdate Pydantic model, which
    returns HTTP 422 automatically on failure. When a new status is
    supplied, the (current -> new) transition is additionally validated.
    """
    if payload.status is not None:
        existing = storage.get_task_by_id(task_id)
        if existing is None:
            raise HTTPException(
                status_code=404,
                detail=f"Task with id {task_id} not found",
            )
        validate_status_transition(existing.status, payload.status)

    task = storage.update_task(task_id, payload)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task with id {task_id} not found",
        )
    return task


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["tasks"],
)
def delete_task(task_id: str) -> None:
    """Delete a task by id. Returns 204 on success, or 404 if it does not exist."""
    if not storage.delete_task(task_id):
        raise HTTPException(
            status_code=404,
            detail=f"Task with id {task_id} not found",
        )


if __name__ == "__main__":
    # Lets the app be started with `python -m app.main` as an
    # alternative to the `uvicorn` command shown above.
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)