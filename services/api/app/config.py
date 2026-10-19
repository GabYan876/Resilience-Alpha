"""Lecture de la configuration et des secrets : seul endroit qui touche à l'environnement."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str  # postgresql+asyncpg://... (asyncpg ignore `sslmode`, utiliser `ssl`)
    probe_token: str  # jeton partagé avec la sonde du moteur de remédiation
    probe_account_iban: str
    sql_echo: bool = False
    pool_size: int = 5

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_url=os.environ["DATABASE_URL"],
            probe_token=os.environ.get("PROBE_TOKEN", ""),
            probe_account_iban=os.environ.get("PROBE_ACCOUNT_IBAN", "TEST-0001"),
            sql_echo=os.environ.get("SQL_ECHO", "0") == "1",
            pool_size=int(os.environ.get("DB_POOL_SIZE", "5")),
        )
