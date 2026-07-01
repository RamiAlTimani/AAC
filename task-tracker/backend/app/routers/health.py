"""
Router for the /health endpoint.

Kept separate from main.py so that future routers (tasks, etc.) can
follow the same pattern: one file per resource, wired together in
main.py via app.include_router(...).
"""
from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, status_code=200)
def get_health() -> HealthResponse:
    """Report that the service is up, along with the current UTC time."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )