"""Ports (DIP) : les cas d'usage ne connaissent que ces interfaces, petites et ciblées (ISP)."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.models import (
    AccessEntry,
    Credentials,
    LedMode,
    LockoutRecord,
    NewUser,
    Profile,
    Role,
)


class UserRepository(Protocol):
    async def create(self, user: NewUser, welcome_balance_cents: int) -> Profile:
        """Crée l'utilisateur ET son compte en une transaction.

        Lève `EmailAlreadyUsed` / `PhoneAlreadyUsed` : l'unicité est garantie par la base,
        pas par une lecture préalable (course entre deux inscriptions simultanées).
        """
        ...

    async def find_by_email(self, email: str) -> Credentials | None: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenIssuer(Protocol):
    def issue(self, user_id: UUID) -> str: ...


class HealthProbe(Protocol):
    async def ping(self) -> bool: ...


class EventPublisher(Protocol):
    """Événement JSON structuré (`service`, `trace_id`, `event`) vers Loki. Jamais de secret."""

    def publish(self, event: str, trace_id: str, **data: object) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime:
        """Heure courante, avec fuseau (injectée pour tester blocage et expirations)."""
        ...


class CameraControl(Protocol):
    """Allume/éteint la caméra de l'agent hôte. Lève `FaceCheckUnavailable` si injoignable."""

    async def start(self) -> None: ...

    async def stop(self) -> None: ...


class FaceVerifier(Protocol):
    async def verify(self, identifier: str) -> bool:
        """Comparaison 1:1 avec le gabarit de `identifier` (jamais de recherche 1:N).

        Lève `FaceCheckUnavailable` si l'agent est en panne ; `False` si visage absent ou différent.
        """
        ...


class StatusLed(Protocol):
    async def set(self, mode: LedMode) -> None:
        """Peut échouer (ESP8266 injoignable) : l'accès ne doit pas en dépendre."""
        ...


class LockoutStore(Protocol):
    async def get(self, identifier: str) -> LockoutRecord: ...

    async def save(self, record: LockoutRecord) -> None: ...

    async def clear(self, identifier: str) -> None: ...


class FaceSessionStore(Protocol):
    """Mémorise « visage reconnu » entre l'étape caméra et l'étape mot de passe."""

    async def grant(self, identifier: str, expires_at: datetime) -> None: ...

    async def consume(self, identifier: str, now: datetime) -> bool:
        """Usage unique : vrai une seule fois, et seulement avant l'expiration."""
        ...


class LockoutRegistry(Protocol):
    """Vue d'administration des blocages (port distinct de `LockoutStore`, ISP)."""

    async def locked(self, now: datetime) -> list[LockoutRecord]: ...

    async def clear(self, identifier: str) -> None: ...


class RoleStore(Protocol):
    """Habilitations du back-office, par identifiant."""

    async def get(self, identifier: str) -> Role | None: ...

    async def set(self, identifier: str, role: Role) -> None: ...

    async def revoke(self, identifier: str) -> None: ...

    async def all(self) -> dict[str, Role]: ...


class AccessJournal(Protocol):
    """Journal des accès au back-office, consultable par les habilités."""

    async def record(self, entry: AccessEntry) -> None: ...

    async def recent(self, limit: int) -> list[AccessEntry]:
        """Les plus récentes d'abord."""
        ...


class AdminTokenIssuer(Protocol):
    """Jeton du back-office, distinct du jeton client : l'API métier doit le refuser."""

    def issue_admin(self, identifier: str) -> str: ...


class AdminTokenVerifier(Protocol):
    def verify_admin(self, token: str) -> str | None:
        """Identifiant porté par un jeton de back-office valide, sinon `None`."""
        ...
