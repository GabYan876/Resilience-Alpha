"""Ports du service de sauvegarde et restauration PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class DatabaseArchive(Protocol):
    def create_backup(self) -> str: ...

    def restore_latest(self, before: datetime | None = None) -> str: ...

    def has_backups(self) -> bool: ...

    def is_database_healthy(self) -> bool: ...


class BackupUnavailable(Exception):
    """Aucune archive PostgreSQL exploitable n'est disponible."""


@dataclass(frozen=True)
class IntegritySnapshot:
    """Compteurs d'intégrité du grand livre (transactions et écritures sont en ajout seul)."""

    transactions: int
    ledger_entries: int
    unbalanced_transactions: int  # transactions dont les écritures ne s'équilibrent pas


class DatabaseIntegrity(Protocol):
    def snapshot(self) -> IntegritySnapshot: ...
