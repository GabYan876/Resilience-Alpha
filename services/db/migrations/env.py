"""Environnement Alembic (asyncpg).

L'URL vient de l'environnement, jamais de `alembic.ini` : aucun secret versionné.
Les migrations utilisent `DATABASE_URL_ADMIN` (rôle propriétaire, seul habilité au DDL),
tandis que l'API tourne avec `app_rw`, qui n'a aucun droit DDL.
"""

from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

_HERE = Path(__file__).resolve().parent


def _add_api_package_to_path() -> None:
    """Rend `app.adapters.persistence.models` importable.

    Deux dispositions : le dépôt (`services/api`) et l'image Docker, où les
    migrations sont copiées dans `/app/db` à côté du paquet `/app/app`.
    """
    candidates = (_HERE.parent.parent / "api", _HERE.parent.parent)
    for candidate in candidates:
        if (candidate / "app" / "adapters" / "persistence" / "models.py").is_file():
            sys.path.insert(0, str(candidate))
            return
    raise RuntimeError(f"paquet `app` introuvable (essayé : {[str(c) for c in candidates]})")


_add_api_package_to_path()

from app.adapters.persistence.models import METADATA  # noqa: E402  (après sys.path)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = METADATA


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL_ADMIN") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL_ADMIN (ou DATABASE_URL) doit être défini")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    config.set_main_option("sqlalchemy.url", _database_url())
    engine = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
