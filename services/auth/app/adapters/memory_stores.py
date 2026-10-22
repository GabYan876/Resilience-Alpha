"""Stockage en mémoire du blocage et de la reconnaissance du visage, et horloge système.

Le blocage en mémoire ne survit pas à un redémarrage de `auth` : l'adaptateur PostgreSQL
(`login_lockouts`, lot L1 persistance) le remplacera derrière le même port `LockoutStore`.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.models import LockoutRecord


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class InMemoryLockoutStore:
    def __init__(self) -> None:
        self._records: dict[str, LockoutRecord] = {}

    async def get(self, identifier: str) -> LockoutRecord:
        return self._records.get(identifier, LockoutRecord(identifier))

    async def save(self, record: LockoutRecord) -> None:
        self._records[record.identifier] = record

    async def clear(self, identifier: str) -> None:
        self._records.pop(identifier, None)


class InMemoryFaceSessionStore:
    def __init__(self) -> None:
        self._grants: dict[str, datetime] = {}

    async def grant(self, identifier: str, expires_at: datetime) -> None:
        self._grants[identifier] = expires_at

    async def consume(self, identifier: str, now: datetime) -> bool:
        expires_at = self._grants.pop(identifier, None)
        return expires_at is not None and now < expires_at
