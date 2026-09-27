"""
Configuration for the Module 4 Admin Dashboard.

All secrets and connection details come from environment variables. For local
development they can be placed in a `.env` file next to this module (see
`.env.example`); real environment variables always take precedence.
"""
import os
from datetime import timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional; plain env vars still work
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent

if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env")


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name, default):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        raise RuntimeError(f"Environment variable {name} must be an integer, got {value!r}.")


def load_config():
    secret_key = os.environ.get("ADMIN_SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "ADMIN_SECRET_KEY is not set. Copy .env.example to .env and set a long random value, "
            "e.g. the output of: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    return {
        "SECRET_KEY": secret_key,

        # Separate cookie so this app never overwrites the main Waste2Value
        # app's default "session" cookie when both run on localhost.
        "SESSION_COOKIE_NAME": "w2v_admin_session",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": _env_bool("ADMIN_COOKIE_SECURE", False),
        "PERMANENT_SESSION_LIFETIME": timedelta(minutes=_env_int("ADMIN_SESSION_MINUTES", 120)),

        # Points at the existing Waste2Value application database.
        "DB_HOST": os.environ.get("DB_HOST", "localhost"),
        "DB_PORT": _env_int("DB_PORT", 3306),
        "DB_USER": os.environ.get("DB_USER", "root"),
        "DB_PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "DB_NAME": os.environ.get("DB_NAME", "waste2value"),

        # Where the main application (Module 2) saves listing images. Module 4
        # only reads from this folder to show listing images to admins.
        "MAIN_UPLOAD_FOLDER": os.environ.get(
            "MAIN_UPLOAD_FOLDER",
            str(BASE_DIR.parent / "main_app" / "static" / "uploads"),
        ),

        "ADMIN_HOST": os.environ.get("ADMIN_HOST", "127.0.0.1"),
        "ADMIN_PORT": _env_int("ADMIN_PORT", 5001),
        "ADMIN_DEBUG": _env_bool("ADMIN_DEBUG", False),
    }
