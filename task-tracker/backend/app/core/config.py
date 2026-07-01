"""
Application configuration.

Loads variables from a local .env file (via python-dotenv) into the
process environment, then exposes them as typed constants with sane
defaults so the rest of the app never touches os.environ directly.
"""
import os

from dotenv import load_dotenv

# Populate os.environ from a .env file if one exists. This is a no-op
# when no .env file is present (e.g. in environments where the real
# environment variables are already set some other way).
load_dotenv()

# Port the Uvicorn server binds to when run via `python -m app.main`.
PORT: int = int(os.getenv("PORT", "8000"))

# Current runtime environment, e.g. "development" or "production".
APP_ENV: str = os.getenv("APP_ENV", "development")