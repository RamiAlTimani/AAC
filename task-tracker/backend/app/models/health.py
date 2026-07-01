"""
Pydantic schemas for the /health endpoint.
"""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response body returned by GET /health."""

    # Overall service status. Always "ok" when the process can respond.
    status: str

    # Current server time, in ISO 8601 format (UTC).
    timestamp: str