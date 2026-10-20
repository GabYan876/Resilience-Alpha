"""Configuration et secrets du service de récupération."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database: str
    backup_dir: Path
    backup_interval_s: int
    backup_retention: int
    pg_host: str
    pg_port: int
    pg_user: str
    pg_password: str
    probe_token: str

    @classmethod
    def from_env(cls) -> Settings:
        token = os.environ.get("PROBE_TOKEN", "")
        if not token:
            raise ValueError(
                "PROBE_TOKEN est obligatoire pour le service de récupération"
            )
        password = os.environ.get("POSTGRES_PASSWORD", "")
        if not password:
            raise ValueError(
                "POSTGRES_PASSWORD est obligatoire pour le service de récupération"
            )
        return cls(
            database=os.environ.get("POSTGRES_DB", "resilience"),
            backup_dir=Path(os.environ.get("DB_BACKUP_PATH", "/backups")),
            backup_interval_s=int(os.environ.get("DB_BACKUP_INTERVAL_S", "300")),
            backup_retention=int(os.environ.get("DB_BACKUP_RETENTION", "12")),
            pg_host=os.environ.get("PGHOST", "postgres"),
            pg_port=int(os.environ.get("PGPORT", "5432")),
            pg_user=os.environ.get("POSTGRES_USER", "resilience_owner"),
            pg_password=password,
            probe_token=token,
        )
