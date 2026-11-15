"""Load and update secrets stored in the project .env file."""

import os
from pathlib import Path

from dotenv import load_dotenv, set_key, unset_key


ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def load_environment() -> None:
    """Load project environment variables without replacing existing values."""
    load_dotenv(ENV_FILE, override=False)


def save_secret(name: str, value: str) -> None:
    """Persist a secret in .env and update the current process environment."""
    set_key(str(ENV_FILE), name, value, quote_mode="always")
    os.environ[name] = value


def remove_secret(name: str) -> None:
    """Remove a consumed secret from .env and the current process environment."""
    unset_key(str(ENV_FILE), name)
    os.environ.pop(name, None)