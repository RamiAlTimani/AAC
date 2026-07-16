"""
Application entry point.

Creates the FastAPI app instance, configures CORS, and registers routers.
Endpoint definitions live in app/routers/. Run it with:
    uvicorn app.main:app --reload
or directly with:
    python -m app.main
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import PORT
from app.routers import health, tasks

# The FastAPI application instance. Uvicorn looks for this object
# when started as `uvicorn app.main:app`.
app = FastAPI(
    title="Task Tracker API",
    description="REST API backend for the Task Tracker learning project.",
    version="0.1.0",
)

# Allow the local frontend (served by Live Server) to read API responses from
# the browser. Scoped to the known dev origin only — not a wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(tasks.router)


if __name__ == "__main__":
    # Lets the app be started with `python -m app.main` as an
    # alternative to the `uvicorn` command shown above.
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
