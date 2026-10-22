"""Administration du back-office : habilitations, déblocage d'un identifiant, journal d'accès.

Chaque appel relit le rôle de l'acteur : un retrait d'habilitation prend effet tout de suite,
sans attendre l'expiration de son jeton. `operator` lit, seul `admin` modifie.
L'enrôlement et la révocation d'un visage restent en ligne de commande sur le PC Hôte
(`host-agent/camera`) : le gabarit ne transite jamais par le réseau ni par ce service.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import uuid4

from app.domain.errors import CannotRevokeSelf, NotAuthorized, UnknownUser
from app.domain.models import AccessEntry, LockoutRecord, Role
from app.domain.ports import (
    AccessJournal,
    Clock,
    EventPublisher,
    LockoutRegistry,
    RoleStore,
    UserRepository,
)


@dataclass(frozen=True)
class Habilitation:
    identifier: str
    role: Role


class BackOfficeAdmin:
    def __init__(
        self,
        users: UserRepository,
        roles: RoleStore,
        lockouts: LockoutRegistry,
        journal: AccessJournal,
        clock: Clock,
        publisher: EventPublisher,
    ) -> None:
        self._users = users
        self._roles = roles
        self._lockouts = lockouts
        self._journal = journal
        self._clock = clock
        self._publisher = publisher

    async def whoami(self, actor: str) -> Role:
        return await self._authorize(actor, Role.OPERATOR)

    async def habilitations(self, actor: str) -> list[Habilitation]:
        await self._authorize(actor, Role.OPERATOR)
        return [Habilitation(i, r) for i, r in (await self._roles.all()).items()]

    async def grant(self, actor: str, identifier: str, role: Role) -> None:
        await self._authorize(actor, Role.ADMIN)
        if await self._users.find_by_email(identifier) is None:
            raise UnknownUser("aucun compte pour cet identifiant")
        await self._roles.set(identifier, role)
        await self._emit("auth.admin.role_granted", actor, identifier, role.value)

    async def revoke(self, actor: str, identifier: str) -> None:
        await self._authorize(actor, Role.ADMIN)
        if identifier == actor:
            raise CannotRevokeSelf("impossible de retirer sa propre habilitation")
        await self._roles.revoke(identifier)
        await self._emit("auth.admin.role_revoked", actor, identifier)

    async def lockouts(self, actor: str) -> list[LockoutRecord]:
        await self._authorize(actor, Role.OPERATOR)
        return await self._lockouts.locked(self._clock.now())

    async def unlock(self, actor: str, identifier: str) -> None:
        await self._authorize(actor, Role.ADMIN)
        await self._lockouts.clear(identifier)
        await self._emit("auth.admin.unlocked", actor, identifier)

    async def journal(self, actor: str, limit: int = 100) -> list[AccessEntry]:
        await self._authorize(actor, Role.OPERATOR)
        return await self._journal.recent(limit)

    async def _authorize(self, actor: str, required: Role) -> Role:
        role = await self._roles.get(actor)
        if role is None or (required is Role.ADMIN and role is not Role.ADMIN):
            self._publisher.publish("auth.admin.forbidden", uuid4().hex, actor_hash=_digest(actor))
            raise NotAuthorized("habilitation insuffisante")
        return role

    async def _emit(self, event: str, actor: str, target: str, detail: str = "") -> None:
        # Loki : empreintes seulement. Journal du back-office : lisible, avec l'auteur.
        self._publisher.publish(
            event, uuid4().hex, actor_hash=_digest(actor), identifier_hash=_digest(target)
        )
        text = f"par {actor}" + (f" ({detail})" if detail else "")
        await self._journal.record(AccessEntry(self._clock.now(), event, target, text))


def _digest(identifier: str) -> str:
    return hashlib.sha256(identifier.encode()).hexdigest()[:12]
