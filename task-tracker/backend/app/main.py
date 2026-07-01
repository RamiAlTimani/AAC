"""
Application entry point.

Creates the FastAPI app instance and registers routers. Run it with:
    uvicorn app.main:app --reload
or directly with:
    python -m app.main
"""
import uvicorn
from fastapi import FastAPI

from app.core.config import PORT
from app.routers import health

# The FastAPI application instance. Uvicorn looks for this object
# when started as `uvicorn app.main:app`.
app = FastAPI(
    title="Task Tracker API",
    description="REST API backend for the Task Tracker learning project.",
    version="0.1.0",
)

# Mount the health-check router.
app.include_router(health.router)


if __name__ == "__main__":
    # Lets the app be started with `python -m app.main` as an
    # alternative to the `uvicorn` command shown above.
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)