"""Adaptateurs de sécurité : hachage argon2 et jetons JWT (HS256)."""

from __future__ import annotations

import time
from uuid import UUID

import jwt
from argon2 import PasswordHasher as Argon2
from argon2.exceptions import InvalidHashError, VerificationError


class Argon2PasswordHasher:
    """Implémente le port `PasswordHasher` (mêmes paramètres que le seed de l'API)."""

    def __init__(self) -> None:
        self._argon2 = Argon2()

    def hash(self, password: str) -> str:
        return self._argon2.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return self._argon2.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False


class JwtTokenIssuer:
    """Implémente le port `TokenIssuer`. L'API métier vérifie avec le même secret."""

    def __init__(self, secret: str, ttl_seconds: int) -> None:
        self._secret = secret
        self._ttl_seconds = ttl_seconds

    def issue(self, user_id: UUID) -> str:
        now = int(time.time())
        claims = {"sub": str(user_id), "iat": now, "exp": now + self._ttl_seconds}
        return jwt.encode(claims, self._secret, algorithm="HS256")
