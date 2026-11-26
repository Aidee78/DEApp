"""Load the project environment and remove migrated legacy entries."""

import os
from pathlib import Path

from dotenv import load_dotenv, unset_key


ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def load_environment() -> None:
    """Load project environment variables without replacing existing values."""
    load_dotenv(ENV_FILE, override=False)


def remove_secret(name: str) -> None:
    """Remove a migrated secret from .env and the current process environment."""
    unset_key(str(ENV_FILE), name)
    os.environ.pop(name, None)
