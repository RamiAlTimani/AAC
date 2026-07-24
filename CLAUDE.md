# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Task Tracker is a Module 4 learning project for the AUB "AI Assisted Coding" course: a FastAPI + Pydantic v2 REST API with an in-memory store, paired with a dependency-free static HTML/CSS/JS Kanban frontend. There is **no database, ORM, or persistence** (a deliberate decision — see `docs/midcourse/mini-adr.md`); restarting the backend clears all tasks.

## 1. Tech stack

- **Python 3.11** — the course runtime. `[VERIFY]` the repo `README.md` states "Python 3.10 or later" and `requirements.txt` pins no Python version.
- **FastAPI** 0.139.0 — web framework
- **Pydantic v2** 2.13.4 — request/response validation
- **Uvicorn** 0.49.0 (`uvicorn[standard]`) — ASGI server
- **pytest** 9.1.1 — test runner
- **httpx** 0.28.1 — used by FastAPI's `TestClient` in tests
- **python-dotenv** 1.2.2 — loads `.env` in `app/core/config.py`
- **Vanilla JavaScript frontend** — `task-tracker/frontend/`, no framework or build step

Versions above are the exact pins in `task-tracker/backend/requirements.txt`.

## 2. Run command

From `task-tracker/backend/` with the venv active:

```bash
uvicorn app.main:app --reload --port 8000
```

The API is then at `http://localhost:8000` (interactive docs at `/docs`).

## 3. Test command

From `task-tracker/backend/` with the venv active:

```bash
pytest -v
```

Tests drive the app in-process via `TestClient`, so the Uvicorn server does **not** need to be running.

## 4. Architecture

Request flow: `main.py` (app + CORS + router registration) → `routers/{health,tasks}.py` (HTTP endpoints, one file per resource) → `storage.py` (in-memory dict) — with `models.py` and `business_rules.py` alongside.

**Backend** (`task-tracker/backend/app/`):
- `main.py` — creates the FastAPI app, adds CORS, registers routers.
- `routers/tasks.py` — the five `/tasks` endpoints (create, list, get, patch, delete).
- `routers/health.py` — `GET /health`.
- `models.py` — Pydantic schemas (`TaskCreate`, `TaskUpdate`, `TaskResponse`, `HealthResponse`) and the `TaskStatus` / `TaskPriority` enums.
- `storage.py` — module-level `_tasks: dict[str, TaskResponse]`, plus `_reset()` for tests.
- `business_rules.py` — cross-field / stateful rules (status transitions, due-date changes).
- `core/config.py` — loads `.env`, exposes `PORT` and `APP_ENV`.

**Frontend** (`task-tracker/frontend/`): `index.html`, `style.css`, `app.js` (single vanilla-JS file; the fetched task list is the source of truth).

**Tests** (`task-tracker/backend/tests/`): `conftest.py` (autouse fixture resets `storage` around each test; real store, no mocking), `test_tasks.py`, `test_due_dates.py`, `test_tags.py`.

**Where task rules live** — the key boundary:
- **`models.py`** holds per-field validation that needs only the incoming value (title length, tag normalization, `due_date` not-in-the-past on *create*). All task models use `extra="forbid"`, so unknown fields are a 422.
- **`business_rules.py`** holds rules that need the *existing* task, so they can't be field validators. The router in `routers/tasks.py` looks up the existing task up front when `status` or `due_date` is present (which also makes 404 take precedence over 422).

## 5. Business rules

**Status values** (`TaskStatus` in `models.py`): `ToDo`, `InProgress`, `Done`.
**Priority values** (`TaskPriority`): `Low`, `Medium`, `High`.

**Status transitions** — `validate_status_transition` in `business_rules.py` allows exactly these `current → new` moves (`VALID_TRANSITIONS`); anything else raises 422:

- `ToDo → InProgress`
- `InProgress → Done`
- `Done → InProgress`

Same → same is **not** allowed (it isn't in the set). Any transition not listed (e.g. `ToDo → Done`, `InProgress → ToDo`) is rejected.

**Other rules** (from `models.py` / `business_rules.py`): title is stripped and must be 1–200 chars; tags are trimmed, blank tags dropped, deduped case-insensitively (first casing wins), each ≤30 chars, max 10 after dedupe; `due_date` cannot be earlier than today on create; on update, clearing the date or resending the existing date is allowed but moving it to a new past date is rejected.

## 6. UI states and CORS

**UI states** — `app.js` drives the board through three states via `setBoardState`: `loading` (spinner), `ready` (columns shown, including empty ones), and `error` (message + Retry button). Status changes use optimistic drag-and-drop that reverts and shows a toast if the server rejects the move.

**CORS** — configured in `main.py`. Allowed origins are `http://localhost:5500` and `http://127.0.0.1:5500` only (not a wildcard), with all methods and headers allowed. The frontend must therefore be served on **port 5500** (e.g. `python3 -m http.server 5500` from `task-tracker/frontend/`, or VS Code Live Server).

## 7. Do-not rules

Do not, without asking first:
- add authentication or authorization,
- introduce a database, ORM, or any persistence layer (the in-memory store is an intentional decision),
- add deployment steps, containers, or cloud/production configuration,
- make major UI changes or restructure the frontend.

Also: do not change application code when the task is only to update docs.
