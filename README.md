
# Task Tracker

Task Tracker is a learning-focused REST API for creating, viewing, and managing tasks, built with Python, FastAPI, and Pydantic. This repository currently contains the initial backend skeleton and a health-check endpoint; task management endpoints and the static frontend will be added in later iterations.

## Prerequisites

- Python 3.10 or later

## 1. Create a virtual environment and install dependencies

All commands below run from inside the `backend/` folder.

**macOS / Linux**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Then copy the example environment file:

**macOS / Linux**: `cp .env.example .env`
**Windows (PowerShell)**: `Copy-Item .env.example .env`

## 2. Start the server with uvicorn

With the virtual environment active and your working directory at `backend/`:

```bash
uvicorn app.main:app --reload --port 8000
```

The API is now available at `http://localhost:8000` (interactive docs at `/docs`).

## 3. Test the health endpoint

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
