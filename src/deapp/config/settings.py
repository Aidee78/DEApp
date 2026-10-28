"""Load and validate non-secret application settings."""

from dataclasses import dataclass
from pathlib import Path
import tomllib


# Settings is the typed container for validated, non-secret configuration. load_settings()
# reads config/config.toml, checks that required values are valid, resolves the configured 
# paths, and returns a Settings instance.
# The application entry point would load it once at startup

# Then pass settings to the parts of the application that need it:
# - Logging setup uses settings.log_level and settings.log_file.
# - State management uses settings.state_file.
# - Application orchestration can receive settings and pass relevant settings to the services
# it starts.

# create a dataclass and make its instances immutable after creation.
@dataclass(frozen=True)
class Settings:
    """Validated settings that describe how DEApp runs."""

    app_name: str
    log_level: str
    state_file: Path
    log_file: Path


def load_settings(config_path: Path | None = None) -> Settings:
    """Load settings from TOML and resolve configured paths.

    Relative paths are resolved from the project root, taken as the
    parent directory of the config directory.
    """
    if config_path is None:
        config_path = Path("config/config.toml")

    config_path = config_path.resolve()

    try:
        with config_path.open("rb") as config_file:
            raw = tomllib.load(config_file) 
    except FileNotFoundError as error:
        raise ValueError(f"Configuration file not found: {config_path}") from error
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"Configuration file is invalid TOML: {config_path}") from error

    application = raw.get("application")
    paths = raw.get("paths")

    if not isinstance(application, dict):
        raise ValueError("Missing or invalid [application] section")
    if not isinstance(paths, dict):
        raise ValueError("Missing or invalid [paths] section")

    app_name: str | None = application.get("name")
    log_level: str | None = application.get("log_level")
    state_file_value: str | None = paths.get("state_file")
    log_file_value: str | None = paths.get("log_file")

    missing = [
        name
        for name, value in (
            ("application.name", app_name),
            ("application.log_level", log_level),
            ("paths.state_file", state_file_value),
            ("paths.log_file", log_file_value),
        )
        if not isinstance(value, str) or not value.strip()
    ] # ensure we got the appropriate configurations and as non-empty strings

    if missing:
        raise ValueError(f"Missing or invalid settings: {', '.join(missing)}")

    normalized_log_level = log_level.upper()

    if normalized_log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("Invalid setting: application.log_level")


    PROJECT_ROOT = config_path.parent.parent

    def resolve_path(value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return (PROJECT_ROOT / path).resolve()

    return Settings(
        app_name=app_name,
        log_level=normalized_log_level,
        state_file=resolve_path(state_file_value),
        log_file=resolve_path(log_file_value),
    )