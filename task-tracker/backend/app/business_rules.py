"""
Business rules for tasks that go beyond per-field schema validation.

These rules depend on relationships between values (e.g. the current and
proposed status of a task), so they live here rather than in the Pydantic
models, which validate fields in isolation.
"""
from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError

from app.models import TaskStatus

# Allowed (current -> new) status transitions. Anything not listed here is
# rejected, which means same -> same is invalid by construction.
VALID_TRANSITIONS: frozenset[tuple[TaskStatus, TaskStatus]] = frozenset({
    (TaskStatus.TODO, TaskStatus.IN_PROGRESS),
    (TaskStatus.IN_PROGRESS, TaskStatus.DONE),
    (TaskStatus.DONE, TaskStatus.IN_PROGRESS),
})


def validate_status_transition(current: TaskStatus, new: TaskStatus) -> None:
    """Validate a status transition, raising on a disallowed move.

    Only the pairs in VALID_TRANSITIONS are permitted; every other pair,
    including same -> same, is rejected.

    Args:
        current: The task's existing status.
        new: The status the caller wants to move to.

    Raises:
        HTTPException: 422 Unprocessable Entity if (current, new) is not in
            VALID_TRANSITIONS. The detail lists the allowed transitions.
    """
    if (current, new) not in VALID_TRANSITIONS:
        allowed = sorted({f"{f.value}->{t.value}" for f, t in VALID_TRANSITIONS})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid status transition from {current.value} to {new.value}. "
                f"Allowed transitions: {allowed}"
            ),
        )


def validate_due_date_change(current: Optional[date], new: Optional[date]) -> None:
    """Validate a due-date change, raising if it moves the date into the past.

    Clearing the date (``new`` is None) is always allowed (DD-2), as is
    resending the date the task already has even once that date is in the past:
    a task validly created with a future due date must stay editable after that
    date passes, and the edit modal resends the unchanged due_date. Only moving
    the due date to a new date earlier than today is rejected (DD-5). Telling
    "changing the date" from "resending the same date" needs the existing task,
    which is why this is a business rule rather than a field_validator on
    TaskUpdate.

    Args:
        current: The task's existing due date, or None if it had none.
        new: The proposed due date, or None to clear it.

    Raises:
        RequestValidationError: If ``new`` is a date earlier than today and
            differs from ``current``. It is raised (rather than an
            HTTPException) with loc ("body", "due_date") so contract B8 can
            route the error to the due-date input; HTTPException's string detail
            has no loc.
    """
    if new is None:
        return
    if new == current:
        return
    if new < date.today():
        raise RequestValidationError([
            {
                "type": "value_error",
                "loc": ("body", "due_date"),
                "msg": "due_date must not be earlier than today",
                "input": new,
            }
        ])
