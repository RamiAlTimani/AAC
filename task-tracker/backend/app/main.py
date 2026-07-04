"""
Application entry point.

Creates the FastAPI app instance and registers routers. Run it with:
    uvicorn app.main:app --reload
or directly with:
    python -m app.main
"""
import uvicorn
from fastapi import FastAPI, status

from app.core.config import PORT
from app.models import TaskCreate, TaskStatus, TaskPriority, TaskResponse
from app.routers import health
from app import storage

# The FastAPI application instance. Uvicorn looks for this object
# when started as `uvicorn app.main:app`.
app = FastAPI(
    title="Task Tracker API",
    description="REST API backend for the Task Tracker learning project.",
    version="0.1.0",
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


if __name__ == "__main__":
    # Lets the app be started with `python -m app.main` as an
    # alternative to the `uvicorn` command shown above.
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)