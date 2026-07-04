"""
Pydantic v2 schemas and enums for the Task Tracker API.

Single home for all request/response models: the Task schemas used by the
in-memory storage layer, plus the health-check schema (relocated here from
the former app/models/ package). No database or ORM is involved.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


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


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: Optional[str] = ""
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee: Optional[str] = None

    @field_validator("title")
    @classmethod
    def _check_title(cls, value: str) -> str:
        return _validate_title(value)


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee: Optional[str] = None

    @field_validator("title")
    @classmethod
    def _check_title(cls, value: Optional[str]) -> Optional[str]:
        # Only validate when a title is actually provided.
        if value is None:
            return value
        return _validate_title(value)


class TaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee: Optional[str]
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    """Response body returned by GET /health."""

    # Overall service status. Always "ok" when the process can respond.
    status: str

    # Current server time, in ISO 8601 format (UTC).
    timestamp: str
