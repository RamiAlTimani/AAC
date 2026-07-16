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
    """Raise 422 if moving from ``current`` to ``new`` is not permitted.

    Same -> same is invalid. Anything not in VALID_TRANSITIONS is invalid.
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
    """Raise 422 if ``new`` moves a task's due date into the past (DD-5).

    Clearing the date (``new`` is None) is always allowed (DD-2). So is resending
    the date the task already has, even once that date is in the past: a task
    validly created with a future due date must stay editable after that date
    passes, and the edit modal resends the unchanged due_date. Telling "changing
    the date" from "resending the same date" needs the existing task, which is why
    this is a business rule rather than a field_validator on TaskUpdate.

    Raises RequestValidationError, not HTTPException, because DD-5 puts the error
    on the due-date input: contract B8 routes an error to its input slot by reading
    the ``loc`` path, and HTTPException's string detail has no loc.
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
