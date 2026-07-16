"""
Router for the /tasks endpoints.

Holds the five task endpoints moved verbatim out of main.py, following the
same one-file-per-resource pattern as health.py. Behaviour is unchanged:
this is a relocation, not a rewrite.

The router carries the /tasks prefix, so route paths here are "" for the
collection and "/{task_id}" for a single task.
"""
from fastapi import APIRouter, HTTPException, status

from app.business_rules import validate_due_date_change, validate_status_transition
from app.models import TaskCreate, TaskStatus, TaskPriority, TaskResponse, TaskUpdate
from app import storage

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(payload: TaskCreate) -> TaskResponse:
    """Create a new task.

    Validation (required/blank/overlong title, invalid status or priority,
    and unknown fields) is handled entirely by the TaskCreate Pydantic model,
    which returns HTTP 422 automatically on failure. The storage layer assigns
    the id and timestamps.
    """
    return storage.add_task(payload)


@router.get(
    "",
    response_model=list[TaskResponse],
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


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
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


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
)
def update_task(task_id: str, payload: TaskUpdate) -> TaskResponse:
    """Apply a partial update to a task, or 404 if it does not exist.

    Body validation (blank/overlong title, invalid status or priority,
    unknown fields) is handled by the TaskUpdate Pydantic model, which
    returns HTTP 422 automatically on failure. When a new status or a new
    due date is supplied, it is additionally validated against the existing
    task, which is why the lookup happens up front for those two cases. That
    ordering also makes 404 take precedence over 422 for a missing task.
    """
    if payload.status is not None or payload.due_date is not None:
        existing = storage.get_task_by_id(task_id)
        if existing is None:
            raise HTTPException(
                status_code=404,
                detail=f"Task with id {task_id} not found",
            )
        if payload.status is not None:
            validate_status_transition(existing.status, payload.status)
        if payload.due_date is not None:
            validate_due_date_change(existing.due_date, payload.due_date)

    task = storage.update_task(task_id, payload)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task with id {task_id} not found",
        )
    return task


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(task_id: str) -> None:
    """Delete a task by id. Returns 204 on success, or 404 if it does not exist."""
    if not storage.delete_task(task_id):
        raise HTTPException(
            status_code=404,
            detail=f"Task with id {task_id} not found",
        )
