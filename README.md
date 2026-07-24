# Task Tracker

Task Tracker is a Module 4 learning project for the American University of Beirut
"AI-Assisted Coding" course. It is a small REST API for creating, viewing, and
managing tasks, built with **Python, FastAPI, and Pydantic v2**, paired with a
dependency-free static **HTML/CSS/JavaScript** Kanban frontend.

Tasks are held in an **in-memory store** — there is no database, ORM, or
persistence, which is a deliberate decision (see
[docs/midcourse/mini-adr.md](docs/midcourse/mini-adr.md)). Restarting the backend
clears all tasks.

> This is a learning project. It is **not** production-ready and includes no
> authentication, no database, and no deployment configuration.

## 1. Project overview

- **Backend** — FastAPI app exposing `GET /health` and five `/tasks` endpoints
  (create, list, get, patch, delete), with request/response validation via
  Pydantic v2 and business rules (status transitions, due-date changes) enforced
  server-side. Interactive API docs are served at `/docs`.
- **Frontend** — a single-page vanilla-JS Kanban board (`index.html`,
  `style.css`, `app.js`) with no framework or build step. The fetched task list
  is the source of truth; status changes use optimistic drag-and-drop.
- **Store** — a module-level dictionary in `app/storage.py`; state lives only in
  the running process.

## 2. Prerequisites

- **Python 3.11** — the course runtime (used by CI and the Docker image).
- **pip** and the ability to create a virtual environment (`venv`).
- **Docker** — only needed for the "Run with Docker" section.

## 3. Local setup

All backend work happens in `task-tracker/backend/`. From the **repo root**:

**macOS / Linux**

```bash
cd task-tracker/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

**Windows (PowerShell)**

```powershell
cd task-tracker\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` sets `PORT` (default `8000`) and `APP_ENV` (default `development`), loaded
by `app/core/config.py`.

## 4. Run the app locally

With the virtual environment active, from `task-tracker/backend/`:

```bash
uvicorn app.main:app --reload --port 8000
```

The API is then at `http://localhost:8000` (interactive docs at `/docs`). Verify
it is up:

```bash
curl http://localhost:8000/health
```

Expected response (HTTP 200):

```json
{ "status": "ok", "timestamp": "2026-07-01T12:00:00.000000+00:00" }
```

### Serve the frontend

The frontend is static files and **must** be served on port `5500` — that is the
only origin the backend allows through CORS. In a second terminal, from the
**repo root**:

**macOS / Linux**

```bash
cd task-tracker/frontend
python3 -m http.server 5500
```

**Windows (PowerShell)**

```powershell
cd task-tracker\frontend
python -m http.server 5500
```

Then open `http://localhost:5500`. Keep the backend running — the page calls the
API at `http://localhost:8000`. (VS Code "Live Server" also works; it defaults to
port 5500.)

## 5. Run tests

The tests use pytest and drive the app in-process via `TestClient`, so the
uvicorn server does **not** need to be running. With the virtual environment
active, from `task-tracker/backend/`:

```bash
pytest -v
```

Useful variations:

```bash
pytest tests/test_tasks.py     # a single test file
pytest -k due_date             # only tests matching a keyword
```

## 6. Run with Docker

The `Dockerfile` lives in `task-tracker/backend/` and builds a **backend-only**
image (the frontend is not included). From the **repo root**:

```bash
docker build -t task-tracker task-tracker/backend
docker run --rm -p 8000:8000 task-tracker
```

The API is then at `http://localhost:8000`. The container runs
`uvicorn app.main:app --host 0.0.0.0 --port 8000` as a non-root user. Note: the
port is fixed at `8000` in the image and `.env` is not copied in, so `PORT` /
`APP_ENV` from `.env` do not affect the container. To serve the frontend against
this container, run the port-5500 static server from section 4 separately.

## 7. CI workflow summary

`.github/workflows/ci.yml` defines a single `test` job that runs on every `push`
and `pull_request`:

1. Checks out the repository.
2. Sets up **Python 3.11**.
3. Installs dependencies from `task-tracker/backend/requirements.txt`.
4. Runs `pytest -v`.

All steps use `task-tracker/backend/` as the working directory. There is no
build, lint, or deploy step.

## 8. Project structure

```
task-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app: CORS + router registration
│   │   ├── models.py          # Pydantic schemas + TaskStatus / TaskPriority enums
│   │   ├── storage.py         # in-memory dict store (+ _reset for tests)
│   │   ├── business_rules.py  # status-transition & due-date rules
│   │   ├── core/config.py     # loads .env, exposes PORT / APP_ENV
│   │   └── routers/
│   │       ├── health.py      # GET /health
│   │       └── tasks.py       # the five /tasks endpoints
│   ├── tests/                 # conftest.py + test_tasks / test_due_dates / test_tags
│   ├── requirements.txt       # pinned dependencies
│   ├── Dockerfile             # multi-stage, backend-only image
│   └── .env.example
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js                 # single vanilla-JS file
```

## 9. Conventions and current limitations

**Conventions**

- One router file per resource (`routers/health.py`, `routers/tasks.py`), wired
  together in `main.py`.
- **Per-field validation** (title length, tag normalization, create-time
  due-date) lives in `models.py`; all task models use `extra="forbid"`, so
  unknown fields return 422. **Cross-field / stateful rules** that need the
  existing task (status transitions, due-date changes on update) live in
  `business_rules.py`.
- Allowed status transitions: `ToDo → InProgress`, `InProgress → Done`,
  `Done → InProgress` (same → same and anything else is rejected with 422).
- Tests use the real store with an autouse fixture that resets it around each
  test (no mocking).

**Limitations** (by design for this module)

- **No persistence** — restarting the backend clears all tasks.
- **No authentication or authorization.**
- **No database or ORM.**
- **CORS is scoped to `http://localhost:5500` / `http://127.0.0.1:5500` only**,
  so the frontend must be served on port 5500.
- **Not production-ready** — no deployment or cloud configuration is provided.

## 10. Technical decisions

The choice to keep an in-memory store (rather than adopt a database for the Due
Dates and Tags features) is documented in the mini-ADR:

- [docs/midcourse/mini-adr.md](docs/midcourse/mini-adr.md) — Storage architecture
  for Due Dates & Tags.

Related course notes live under [docs/midcourse/](docs/midcourse/).
