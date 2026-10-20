"""API privée de contrôle des sauvegardes et de la restauration."""

from __future__ import annotations

import hmac
import subprocess
from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.application.recovery import DatabaseRecoveryService
from app.domain.ports import BackupUnavailable


def build_router(
    recovery: DatabaseRecoveryService,
    get_probe_token: Callable[[], str],
    publish_event: Callable[..., None],
) -> APIRouter:
    router = APIRouter()

    def require_probe_token(authorization: str = Header(default="")) -> None:
        expected = get_probe_token()
        supplied = authorization.removeprefix("Bearer ")
        if not expected or not hmac.compare_digest(supplied, expected):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "jeton invalide")

    @router.get("/health")
    async def health() -> dict[str, str]:
        healthy = await run_in_threadpool(recovery.is_database_healthy)
        if not healthy:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "base ou sauvegarde initiale indisponible"
            )
        return {"status": "ok"}

    @router.post("/backup", dependencies=[Depends(require_probe_token)])
    async def create_backup() -> dict[str, str]:
        try:
            archive = await run_in_threadpool(recovery.create_backup)
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            publish_event("database.backup.failed", error=type(exc).__name__)
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "sauvegarde PostgreSQL impossible"
            ) from exc
        publish_event("database.backup.created", archive=archive)
        return {"status": "ok", "archive": archive}

    @router.post("/restore", dependencies=[Depends(require_probe_token)])
    async def restore_latest(before: datetime | None = None) -> dict[str, str]:
        try:
            archive = await run_in_threadpool(recovery.restore_latest, before)
        except BackupUnavailable as exc:
            publish_event("database.restore.failed", error="backup_unavailable")
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "aucune sauvegarde disponible"
            ) from exc
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            publish_event("database.restore.failed", error=type(exc).__name__)
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "restauration PostgreSQL impossible",
            ) from exc
        publish_event("database.restore.completed", archive=archive)
        return {"status": "ok", "archive": archive}

    return router
