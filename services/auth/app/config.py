"""Lecture de la configuration et des secrets : seul endroit qui touche à l'environnement."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _read_jwt_secret() -> str:
    """Fichier d'abord (rotation : `RotateSecretAction` écrit sur un volume partagé, relu ici à
    chaque démarrage), sinon la variable d'environnement (premier démarrage, pas encore de
    rotation)."""
    file_path = os.environ.get("JWT_SECRET_FILE")
    if file_path and os.path.exists(file_path):
        with open(file_path, encoding="utf-8") as handle:
            return handle.read().strip()
    return os.environ["JWT_SECRET"]  # KeyError volontaire : aucun secret par défaut


@dataclass(frozen=True)
class Settings:
    database_url: str  # postgresql+asyncpg://app_rw:... (jamais le rôle propriétaire)
    jwt_secret: str  # partagé avec l'API métier, qui vérifie les jetons
    jwt_ttl_seconds: int = 7200
    # Solde de bienvenue fictif (centimes) : démonstration uniquement, aucune valeur réelle.
    welcome_balance_cents: int = 100_000

    @classmethod
    def from_env(cls) -> Settings:
        secret = _read_jwt_secret()
        if len(secret) < 32:
            raise ValueError("JWT_SECRET doit contenir au moins 32 caractères")
        return cls(
            database_url=os.environ["DATABASE_URL"],
            jwt_secret=secret,
            jwt_ttl_seconds=int(os.environ.get("JWT_TTL_SECONDS", "7200")),
            welcome_balance_cents=int(os.environ.get("WELCOME_BALANCE_CENTS", "100000")),
        )
