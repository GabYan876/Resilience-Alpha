"""Lecture de la configuration et des secrets : seul endroit qui touche à l'environnement."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str  # postgresql+asyncpg://app_rw:... (jamais le rôle propriétaire)
    jwt_secret: str  # partagé avec l'API métier, qui vérifie les jetons
    jwt_ttl_seconds: int = 7200
    # Solde de bienvenue fictif (centimes) : démonstration uniquement, aucune valeur réelle.
    welcome_balance_cents: int = 100_000

    @classmethod
    def from_env(cls) -> Settings:
        secret = os.environ["JWT_SECRET"]  # KeyError volontaire : aucun secret par défaut
        if len(secret) < 32:
            raise ValueError("JWT_SECRET doit contenir au moins 32 caractères")
        return cls(
            database_url=os.environ["DATABASE_URL"],
            jwt_secret=secret,
            jwt_ttl_seconds=int(os.environ.get("JWT_TTL_SECONDS", "7200")),
            welcome_balance_cents=int(os.environ.get("WELCOME_BALANCE_CENTS", "100000")),
        )
