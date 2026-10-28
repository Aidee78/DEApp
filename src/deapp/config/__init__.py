"""Application configuration."""

from deapp.config.environment import load_secrets
from deapp.config.settings import Settings, load_settings

__all__ = ["Settings", "load_settings", "load_secrets"]