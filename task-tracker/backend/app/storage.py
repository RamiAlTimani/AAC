"""
In-memory storage layer for tasks.

Backed by a module-level dictionary keyed by task id. State lives only in
the running process and is cleared between tests via _reset(). No database,
ORM, or external persistence is involved.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.models import (
    TaskCreate,
    TaskPriority,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
)

_tasks: dict[str, TaskResponse] = {}


def _now() -> datetime:
    """Current UTC time. Centralized so created_at/updated_at stay consistent."""
    return datetime.now(timezone.utc)


def add_task(payload: TaskCreate) -> TaskResponse:
    """Create and store a new task, returning its stored representation.

    Generates a UUID id and sets created_at and updated_at to the same
    current UTC timestamp. The tag list is copied so the stored task never
    shares a list object with the caller's payload, and a missing or empty
    description is stored as "".

    Args:
        payload: The validated fields to create the task from.

    Returns:
        The newly created and stored task, including its generated id and
        timestamps.
    """
    task_id = str(uuid4())
    now = _now()
    task = TaskResponse(
        id=task_id,
        title=payload.title,
        description=payload.description or "",
        status=payload.status,
        priority=payload.priority,
        assignee=payload.assignee,
        due_date=payload.due_date,
        # Copy: never share the payload's list object with the stored task.
        tags=list(payload.tags),
        created_at=now,
        updated_at=now,
    )
    _tasks[task_id] = task
    return task


def get_all_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
) -> list[TaskResponse]:
    """Return all tasks, optionally filtered by status and/or priority.

    When both filters are given, a task must match both to be included.
    Passing None for a filter leaves that dimension unfiltered.

    Args:
        status: If given, keep only tasks with this status.
        priority: If given, keep only tasks with this priority.

    Returns:
        The matching tasks in insertion (creation) order. May be empty.
    """
    tasks = list(_tasks.values())
    if status is not None:
        tasks = [t for t in tasks if t.status == status]
    if priority is not None:
        tasks = [t for t in tasks if t.priority == priority]
    return tasks


def get_task_by_id(task_id: str) -> Optional[TaskResponse]:
    """Return the task with the given id, or None if it does not exist.

    Args:
        task_id: The id of the task to look up.

    Returns:
        The matching task, or None if no task has that id.
    """
    return _tasks.get(task_id)


def update_task(task_id: str, payload: TaskUpdate) -> Optional[TaskResponse]:
    """Apply a partial update to a stored task.

    Only fields explicitly set on the payload are applied (exclude_unset), so
    unset fields keep their current values. updated_at is bumped to the current
    UTC time only when at least one field changes; an empty update leaves the
    task untouched. Changes are applied via model_copy, which does not re-run
    the field validators.

    Args:
        task_id: The id of the task to update.
        payload: The partial update to apply.

    Returns:
        The updated task; the unchanged task if the payload set no fields; or
        None if no task has that id.
    """
    task = _tasks.get(task_id)
    if task is None:
        return None

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return task

    # Only bump updated_at when the task actually changes.
    updated = task.model_copy(update={**changes, "updated_at": _now()})
    _tasks[task_id] = updated
    return updated


def delete_task(task_id: str) -> bool:
    """Delete a task by id.

    Args:
        task_id: The id of the task to delete.

    Returns:
        True if a task was removed, False if no task had that id.
    """
    if task_id in _tasks:
        del _tasks[task_id]
        return True
    return False


def _reset() -> None:
    """Clear all stored tasks. For use in tests only."""
    _tasks.clear()
