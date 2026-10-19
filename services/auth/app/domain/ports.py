"""Ports (DIP) : les cas d'usage ne connaissent que ces interfaces, petites et ciblées (ISP)."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.models import Credentials, NewUser, Profile


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
