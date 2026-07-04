"""
Business rules for tasks that go beyond per-field schema validation.

These rules depend on relationships between values (e.g. the current and
proposed status of a task), so they live here rather than in the Pydantic
models, which validate fields in isolation.
"""
from fastapi import HTTPException, status

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
