"""Typed values exchanged by the Dropbox service."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DropboxSnapshot:
    """Remote workbook revision captured when its local copy was downloaded."""

    revision: str
