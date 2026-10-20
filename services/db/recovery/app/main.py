"""Composition root du service de récupération de la base."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapters.postgres_archives import PostgresArchiveStore
from app.adapters.postgres_integrity import PostgresIntegrityProbe
from app.api.routes import build_router
from app.application.recovery import DatabaseRecoveryService
from app.config import Settings
from app.domain.ports import DatabaseArchive, DatabaseIntegrity


def _log_event(event: str, **data: object) -> None:
    print(
        json.dumps(
            {
                "service": "db-recovery",
                "trace_id": uuid.uuid4().hex,
                "event": event,
                **data,
            },
            ensure_ascii=False,
        ),
        file=sys.stdout,
        flush=True,
    )


def create_app(
    settings: Settings | None = None,
    archive: DatabaseArchive | None = None,
    integrity: DatabaseIntegrity | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    if settings.backup_interval_s < 1:
        raise ValueError("DB_BACKUP_INTERVAL_S doit être supérieur ou égal à 1")
    archive = archive or PostgresArchiveStore(
        database=settings.database,
        backup_dir=settings.backup_dir,
        pg_host=settings.pg_host,
        pg_port=settings.pg_port,
        pg_user=settings.pg_user,
        pg_password=settings.pg_password,
        retention=settings.backup_retention,
    )
    integrity = integrity or PostgresIntegrityProbe(
        database=settings.database,
        pg_host=settings.pg_host,
        pg_port=settings.pg_port,
        pg_user=settings.pg_user,
        pg_password=settings.pg_password,
    )
    recovery = DatabaseRecoveryService(archive)

    async def scheduled_backups() -> None:
        while True:
            try:
                name = await asyncio.to_thread(recovery.create_backup)
                _log_event("database.backup.created", archive=name, scheduled=True)
            except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
                _log_event(
                    "database.backup.failed", error=type(exc).__name__, scheduled=True
                )
            await asyncio.sleep(settings.backup_interval_s)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        task = asyncio.create_task(scheduled_backups())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    app = FastAPI(title="db-recovery", lifespan=lifespan)
    app.include_router(
        build_router(
            recovery,
            integrity,
            lambda: settings.probe_token,
            lambda event, **data: _log_event(event, **data),
        )
    )
    return app
