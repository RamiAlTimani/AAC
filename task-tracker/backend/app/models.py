"""
Pydantic v2 schemas and enums for the Task Tracker API.

Single home for all request/response models: the Task schemas used by the
in-memory storage layer, plus the health-check schema (relocated here from
the former app/models/ package). No database or ORM is involved.
"""
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


MAX_TAGS = 10
MAX_TAG_LEN = 30


class TaskStatus(str, Enum):
    TODO = "ToDo"
    IN_PROGRESS = "InProgress"
    DONE = "Done"


class TaskPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


def _validate_title(value: str) -> str:
    """Strip whitespace and enforce a 1..200 character title."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("title must not be blank")
    if len(stripped) > 200:
        raise ValueError("title must be at most 200 characters")
    return stripped


def _normalize_tags(value: list[str]) -> list[str]:
    """Trim, drop blanks, length-check, casefold-dedupe, then count-check."""
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in value:
        stripped = tag.strip()
        # TG-5: a blank tag is dropped, not an error.
        if not stripped:
            continue
        if len(stripped) > MAX_TAG_LEN:
            raise ValueError(f"each tag must be at most {MAX_TAG_LEN} characters")
        # TG-4: first casing seen wins, and surviving order is preserved.
        key = stripped.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(stripped)

    # Counted after deduping, so 11 raw tags collapsing to 10 distinct ones is valid.
    if len(normalized) > MAX_TAGS:
        raise ValueError(f"at most {MAX_TAGS} tags are allowed")
    return normalized


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: Optional[str] = ""
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee: Optional[str] = None
    due_date: Optional[date] = None
    tags: list[str] = []

    @field_validator("title")
    @classmethod
    def _check_title(cls, value: str) -> str:
        return _validate_title(value)

    @field_validator("tags")
    @classmethod
    def _check_tags(cls, value: list[str]) -> list[str]:
        return _normalize_tags(value)

    @field_validator("due_date")
    @classmethod
    def _check_due_date(cls, value: Optional[date]) -> Optional[date]:
        # DD-5: no backdating on create. Today or later is fine; None means no due date.
        if value is not None and value < date.today():
            raise ValueError("due_date must not be earlier than today")
        return value


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee: Optional[str] = None
    # No past-date validator here: telling "changing the date" from "resending the
    # same date" needs the existing task, so that rule lives in business_rules.py.
    due_date: Optional[date] = None
    tags: Optional[list[str]] = None

    @field_validator("title")
    @classmethod
    def _check_title(cls, value: Optional[str]) -> Optional[str]:
        # Only validate when a title is actually provided.
        if value is None:
            return value
        return _validate_title(value)

    @field_validator("tags")
    @classmethod
    def _check_tags(cls, value: Optional[list[str]]) -> list[str]:
        # Reached only when the key is present, so an explicit null is a real None here.
        # TG-2 clears tags with []; update_task applies changes via model_copy, which
        # does not re-validate, so a None slipping through would corrupt the task.
        if value is None:
            raise ValueError("tags must be a list; use [] to clear all tags")
        return _normalize_tags(value)


class TaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee: Optional[str]
    due_date: Optional[date]
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    """Response body returned by GET /health."""

    # Overall service status. Always "ok" when the process can respond.
    status: str

    # Current server time, in ISO 8601 format (UTC).
    timestamp: str
