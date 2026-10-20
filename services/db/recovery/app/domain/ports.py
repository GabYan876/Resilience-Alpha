"""Ports du service de sauvegarde et restauration PostgreSQL."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class DatabaseArchive(Protocol):
    def create_backup(self) -> str: ...

    def restore_latest(self, before: datetime | None = None) -> str: ...

    def has_backups(self) -> bool: ...

    def is_database_healthy(self) -> bool: ...


class BackupUnavailable(Exception):
    """Aucune archive PostgreSQL exploitable n'est disponible."""
