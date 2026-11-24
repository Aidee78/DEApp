"""Tests for non-secret application settings."""

from pathlib import Path

import pytest

from deapp.application.exceptions import ConfigurationError
from deapp.config.settings import load_settings


def write_config(tmp_path: Path, content: str) -> Path:
    """Write a TOML config under a temporary project-like directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    config_path.write_text(content, encoding="utf-8")
    return config_path


def valid_config() -> str:
    return """
[application]
name = "DEApp"
log_level = "info"

[paths]
state_file = "data/state.json"
log_file = "logs/deapp.log"
"""


def test_load_settings_resolves_relative_paths(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, valid_config())

    settings = load_settings(config_path)

    assert settings.app_name == "DEApp"
    assert settings.log_level == "INFO"
    assert settings.state_file == (tmp_path / "data/state.json").resolve()
    assert settings.log_file == (tmp_path / "logs/deapp.log").resolve()


def test_load_settings_rejects_invalid_log_level(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, valid_config().replace('"info"', '"verbose"'))

    with pytest.raises(ConfigurationError, match="application.log_level"):
        load_settings(config_path)


def test_load_settings_rejects_missing_setting(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        valid_config().replace('log_file = "logs/deapp.log"\n', ""),
    )

    with pytest.raises(ConfigurationError, match="paths.log_file"):
        load_settings(config_path)


def test_load_settings_rejects_invalid_toml(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, "[application\n")

    with pytest.raises(ConfigurationError, match="invalid TOML"):
        load_settings(config_path)


def test_load_settings_rejects_missing_file(tmp_path: Path) -> None:
    missing_config = tmp_path / "config" / "config.toml"

    with pytest.raises(ConfigurationError, match="not found"):
        load_settings(missing_config)
