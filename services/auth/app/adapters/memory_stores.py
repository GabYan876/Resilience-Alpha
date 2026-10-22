"""Stockage en mémoire du blocage et de la reconnaissance du visage, et horloge système.

Le blocage, les habilitations et le journal en mémoire ne survivent pas à un redémarrage de
`auth` : les adaptateurs PostgreSQL (`login_lockouts`, `roles`, lot L1 persistance) les
remplaceront derrière les mêmes ports. Les habilitations repartent alors de `BACKOFFICE_ADMINS`.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime

from app.domain.models import AccessEntry, LockoutRecord, Role


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

    async def locked(self, now: datetime) -> list[LockoutRecord]:
        return [r for r in self._records.values() if r.is_locked(now)]


class InMemoryFaceSessionStore:
    def __init__(self) -> None:
        self._grants: dict[str, datetime] = {}

    async def grant(self, identifier: str, expires_at: datetime) -> None:
        self._grants[identifier] = expires_at

    async def consume(self, identifier: str, now: datetime) -> bool:
        expires_at = self._grants.pop(identifier, None)
        return expires_at is not None and now < expires_at


class InMemoryRoleStore:
    def __init__(self, initial: dict[str, Role] | None = None) -> None:
        self._roles: dict[str, Role] = dict(initial or {})

    async def get(self, identifier: str) -> Role | None:
        return self._roles.get(identifier)

    async def set(self, identifier: str, role: Role) -> None:
        self._roles[identifier] = role

    async def revoke(self, identifier: str) -> None:
        self._roles.pop(identifier, None)

    async def all(self) -> dict[str, Role]:
        return dict(sorted(self._roles.items()))


class InMemoryAccessJournal:
    """Tampon circulaire : les plus anciennes lignes sortent, la mémoire reste bornée."""

    def __init__(self, capacity: int = 200) -> None:
        self._entries: deque[AccessEntry] = deque(maxlen=capacity)

    async def record(self, entry: AccessEntry) -> None:
        self._entries.append(entry)

    async def recent(self, limit: int) -> list[AccessEntry]:
        return list(reversed(self._entries))[:limit]
