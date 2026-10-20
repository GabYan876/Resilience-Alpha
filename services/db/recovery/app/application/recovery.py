"""Cas d'usage de sauvegarde/restauration, sérialisés contre les appels concurrents."""

from __future__ import annotations

import threading
from datetime import datetime

from app.domain.ports import DatabaseArchive


class DatabaseRecoveryService:
    def __init__(self, archive: DatabaseArchive) -> None:
        self._archive = archive
        self._lock = threading.Lock()

    def create_backup(self) -> str:
        with self._lock:
            return self._archive.create_backup()

    def restore_latest(self, before: datetime | None = None) -> str:
        with self._lock:
            return self._archive.restore_latest(before)

    def is_database_healthy(self) -> bool:
        return self._archive.is_database_healthy() and self._archive.has_backups()
