"""Load and validate non-secret application settings."""

from dataclasses import dataclass
from pathlib import Path
import tomllib

from deapp.application.exceptions import ConfigurationError


@dataclass(frozen=True)
class Settings:
    """Validated non-secret settings used by the application."""

    app_name: str
    log_level: str
    state_file: Path
    log_file: Path
    dropbox_workbook_path: str | None = None
    dropbox_test_workbook_path: str | None = None


def _require_non_empty_string(
    section: dict[str, object],
    key: str,
    setting_name: str,
) -> str:
    """Return a non-empty string setting or raise a named validation error."""
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"Missing or invalid setting: {setting_name}")
    return value.strip()


def _resolve_path(value: str, project_root: Path) -> Path:
    """Resolve a configured path relative to the project root if needed."""
    path = Path(value)
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


def _optional_dropbox_path(
    section: dict[str, object],
    key: str,
    setting_name: str,
) -> str | None:
    """Return a configured Dropbox file path without inventing a target."""
    value = section.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError(f"Invalid setting: {setting_name}")

    path = value.strip()
    if not path:
        return None
    if not path.startswith("/") or path.endswith("/"):
        raise ConfigurationError(
            f"Invalid setting: {setting_name}; expected a Dropbox file path."
        )
    return path


def load_settings(config_path: Path | None = None) -> Settings:
    """Load TOML settings, validate them, and resolve configured paths."""
    if config_path is None:
        config_path = Path("config/config.toml")

    config_path = config_path.resolve()

    try:
        with config_path.open("rb") as config_file:
            raw: dict[str, object] = tomllib.load(config_file)
    except FileNotFoundError as error:
        raise ConfigurationError(
            f"Configuration file not found: {config_path}"
        ) from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigurationError(
            f"Configuration file is invalid TOML: {config_path}"
        ) from error
    except OSError as error:
        raise ConfigurationError(
            f"Could not read configuration file: {config_path}"
        ) from error

    application_value = raw.get("application")
    paths_value = raw.get("paths")
    dropbox_value = raw.get("dropbox", {})

    if not isinstance(application_value, dict):
        raise ConfigurationError("Missing or invalid [application] section")
    if not isinstance(paths_value, dict):
        raise ConfigurationError("Missing or invalid [paths] section")
    if not isinstance(dropbox_value, dict):
        raise ConfigurationError("Invalid [dropbox] section")

    application: dict[str, object] = application_value
    paths: dict[str, object] = paths_value

    app_name = _require_non_empty_string(application, "name", "application.name")
    log_level = _require_non_empty_string(
        application, "log_level", "application.log_level"
    ).upper()
    state_file = _require_non_empty_string(paths, "state_file", "paths.state_file")
    log_file = _require_non_empty_string(paths, "log_file", "paths.log_file")
    dropbox_workbook_path = _optional_dropbox_path(
        dropbox_value,
        "workbook_path",
        "dropbox.workbook_path",
    )
    dropbox_test_workbook_path = _optional_dropbox_path(
        dropbox_value,
        "test_workbook_path",
        "dropbox.test_workbook_path",
    )
    if (
        dropbox_workbook_path is not None
        and dropbox_test_workbook_path is not None
        and dropbox_workbook_path.casefold()
        == dropbox_test_workbook_path.casefold()
    ):
        raise ConfigurationError(
            "Dropbox production and test workbook paths must be different."
        )

    allowed_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if log_level not in allowed_log_levels:
        raise ConfigurationError("Invalid setting: application.log_level")

    PROJECT_ROOT = config_path.parent.parent

    return Settings(
        app_name=app_name,
        log_level=log_level,
        state_file=_resolve_path(state_file, PROJECT_ROOT),
        log_file=_resolve_path(log_file, PROJECT_ROOT),
        dropbox_workbook_path=dropbox_workbook_path,
        dropbox_test_workbook_path=dropbox_test_workbook_path,
    )
