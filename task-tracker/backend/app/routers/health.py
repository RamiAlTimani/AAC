"""
Router for the /health endpoint.

Kept separate from main.py so that future routers (tasks, etc.) can
follow the same pattern: one file per resource, wired together in
main.py via app.include_router(...).
"""
from datetime import datetime, timezone

from fastapi import APIRouter

from app.models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, status_code=200)
def get_health() -> HealthResponse:
    """Report that the service is up, along with the current UTC time.

    Returns:
        A HealthResponse with status "ok" and the current UTC time as an
        ISO 8601 string.

    Example:
        Request::

            GET /health

        Response (200)::

            {"status": "ok", "timestamp": "2026-07-24T12:00:00+00:00"}
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )