
# Task Tracker

Task Tracker is a learning-focused project built for the AI Assisted Coding course by the American University of Beirut. It is a REST API for creating, viewing, and managing tasks, built with Python, FastAPI, and Pydantic, paired with a static HTML/CSS/JavaScript frontend.

## Prerequisites

- Python 3.10 or later

## 1. Create a virtual environment and install dependencies

All commands below run from inside the `task-tracker/backend/` folder.

**macOS / Linux**

```bash
cd task-tracker/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
cd task-tracker\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Then copy the example environment file:

**macOS / Linux**: `cp .env.example .env`
**Windows (PowerShell)**: `Copy-Item .env.example .env`

## 2. Start the backend server with uvicorn

With the virtual environment active and your working directory at `task-tracker/backend/`:

```bash
uvicorn app.main:app --reload --port 8000
```

The API is now available at `http://localhost:8000` (interactive docs at `/docs`).

## 3. Start the frontend server

The frontend is plain HTML/CSS/JavaScript, so it only needs a static file server. It **must** be served on port `5500` — that is the origin the backend allows through CORS.

In a second terminal, from the repository root:

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

Then open `http://localhost:5500` in your browser. Keep the backend running in the first terminal — the page calls the API at `http://localhost:8000`.

(The VS Code "Live Server" extension also works, since it defaults to port 5500.)

## 4. Run the test suite

The tests use pytest and drive the app in-process, so the uvicorn server does **not** need to be running.

With the virtual environment active and your working directory at `task-tracker/backend/`:

```bash
pytest
```

Useful variations:

```bash
pytest -v                      # verbose, one line per test
pytest tests/test_tasks.py     # a single test file
pytest -k due_date             # only tests matching a keyword
```

## 5. Test the health endpoint

In a separate terminal, with the server still running:

```bash
curl http://localhost:8000/health
```

Expected response (HTTP 200):

```json
{
  "status": "ok",
  "timestamp": "2026-07-01T12:00:00.000000+00:00"
}
```
