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
    return os.environ.get("JWT_SECRET", "")


@dataclass(frozen=True)
class Settings:
    database_url: str  # postgresql+asyncpg://... (asyncpg ignore `sslmode`, utiliser `ssl`)
    probe_token: str  # jeton partagé avec la sonde du moteur de remédiation
    probe_account_iban: str
    jwt_secret: str = ""  # partagé avec `auth` ; vide = routes /me refusent tout jeton
    sql_echo: bool = False
    pool_size: int = 5

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_url=os.environ["DATABASE_URL"],
            probe_token=os.environ.get("PROBE_TOKEN", ""),
            probe_account_iban=os.environ.get("PROBE_ACCOUNT_IBAN", "TEST-0001"),
            jwt_secret=_read_jwt_secret(),
            sql_echo=os.environ.get("SQL_ECHO", "0") == "1",
            pool_size=int(os.environ.get("DB_POOL_SIZE", "5")),
        )
