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

    Field validation (required/blank/overlong title, invalid status or
    priority, unknown fields, and a due_date earlier than today) is handled by
    the TaskCreate model, which returns HTTP 422 automatically on failure. The
    storage layer assigns the id and the created_at/updated_at timestamps.

    Args:
        payload: The validated fields for the new task.

    Returns:
        The created task, including its generated id and timestamps (HTTP 201).

    Example:
        Request::

            POST /tasks
            {"title": "Write docs", "priority": "High"}

        Response (201)::

            {"id": "...", "title": "Write docs", "status": "ToDo",
             "priority": "High", ...}
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

    An empty result is valid and returns 200 with an empty list. Invalid enum
    values in the query string are rejected with 422 by FastAPI. When both
    filters are given, a task must match both.

    Args:
        status: If given, return only tasks with this status.
        priority: If given, return only tasks with this priority.

    Returns:
        The matching tasks in creation order (HTTP 200). May be empty.

    Example:
        Request::

            GET /tasks?status=InProgress

        Response (200)::

            [{"id": "...", "status": "InProgress", ...}]
    """
    return storage.get_all_tasks(status=status, priority=priority)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
def get_task(task_id: str) -> TaskResponse:
    """Fetch a single task by id.

    Args:
        task_id: The id of the task to fetch.

    Returns:
        The matching task (HTTP 200).

    Raises:
        HTTPException: 404 Not Found if no task has the given id.

    Example:
        Request::

            GET /tasks/{task_id}

        Response (200)::

            {"id": "{task_id}", "title": "Write docs", ...}
    """
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
    """Apply a partial update to a task.

    Body validation (blank/overlong title, invalid status or priority, unknown
    fields) is handled by the TaskUpdate model, which returns HTTP 422
    automatically on failure. When a new status or a new due date is supplied,
    it is additionally validated against the existing task, so the task is
    looked up up front for those two cases; that ordering also makes 404 take
    precedence over 422 for a missing task.

    Args:
        task_id: The id of the task to update.
        payload: The partial update to apply.

    Returns:
        The updated task (HTTP 200).

    Raises:
        HTTPException: 404 Not Found if no task has the given id.
        HTTPException: 422 Unprocessable Entity if a supplied status is not a
            valid transition from the task's current status (via
            validate_status_transition).
        RequestValidationError: 422 if a supplied due_date moves the date into
            the past (via validate_due_date_change).

    Example:
        Request::

            PATCH /tasks/{task_id}
            {"status": "InProgress"}

        Response (200)::

            {"id": "{task_id}", "status": "InProgress", ...}
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
    """Delete a task by id.

    Args:
        task_id: The id of the task to delete.

    Returns:
        None, with HTTP 204 No Content on success.

    Raises:
        HTTPException: 404 Not Found if no task has the given id.

    Example:
        Request::

            DELETE /tasks/{task_id}

        Response: 204 No Content (empty body)
    """
    if not storage.delete_task(task_id):
        raise HTTPException(
            status_code=404,
            detail=f"Task with id {task_id} not found",
        )
