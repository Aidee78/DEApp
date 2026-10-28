"""Application configuration."""

from deapp.config.settings import Settings, load_settings
from deapp.config.environment import load_secrets

__all__ = ["Settings", "load_settings", "load_secrets"]