"""Cas d'usage : inscription et connexion, orchestrés via les ports."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import uuid4

from app.domain.errors import InvalidCredentials
from app.domain.models import NewUser, Profile
from app.domain.ports import EventPublisher, PasswordHasher, TokenIssuer, UserRepository


@dataclass(frozen=True)
class AuthResult:
    token: str
    profile: Profile


class RegisterUser:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenIssuer,
        publisher: EventPublisher,
        welcome_balance_cents: int,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        self._publisher = publisher
        self._welcome_balance_cents = welcome_balance_cents

    async def execute(self, *, full_name: str, email: str, phone: str, password: str) -> AuthResult:
        trace_id = uuid4().hex
        # argon2 est volontairement lent : hors de la boucle d'événements.
        password_hash = await asyncio.to_thread(self._hasher.hash, password)
        profile = await self._users.create(
            NewUser(full_name=full_name, email=email, phone=phone, password_hash=password_hash),
            self._welcome_balance_cents,
        )
        self._publisher.publish("auth.registered", trace_id, user_id=str(profile.id))
        return AuthResult(self._tokens.issue(profile.id), profile)


class LoginUser:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenIssuer,
        publisher: EventPublisher,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        self._publisher = publisher

    async def execute(self, *, email: str, password: str) -> AuthResult:
        trace_id = uuid4().hex
        found = await self._users.find_by_email(email)
        if found is None or not await asyncio.to_thread(
            self._hasher.verify, password, found.password_hash
        ):
            # Ni l'e-mail ni le mot de passe dans le journal : seulement le fait de l'échec.
            self._publisher.publish("auth.login_failed", trace_id)
            raise InvalidCredentials("e-mail ou mot de passe incorrect")
        self._publisher.publish("auth.login_succeeded", trace_id, user_id=str(found.profile.id))
        return AuthResult(self._tokens.issue(found.profile.id), found.profile)
