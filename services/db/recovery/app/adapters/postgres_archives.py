"""Archives custom-format PostgreSQL, conservées dans un volume dédié."""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from app.domain.ports import BackupUnavailable


class PostgresArchiveStore:
    def __init__(
        self,
        database: str,
        backup_dir: Path,
        pg_host: str,
        pg_port: int,
        pg_user: str,
        pg_password: str,
        retention: int,
        run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
    ) -> None:
        if retention < 1:
            raise ValueError("DB_BACKUP_RETENTION doit être supérieur ou égal à 1")
        self._database = database
        self._backup_dir = backup_dir
        self._pg_host = pg_host
        self._pg_port = str(pg_port)
        self._pg_user = pg_user
        self._pg_password = pg_password
        self._retention = retention
        self._run = run

    def create_backup(self) -> str:
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        destination = self._backup_dir / f"backup-{timestamp}.dump"
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=self._backup_dir, prefix=".backup-", suffix=".tmp", delete=False
            ) as archive_file:
                temporary = Path(archive_file.name)
            os.chmod(temporary, 0o600)
            self._run(
                [
                    "pg_dump",
                    "--no-password",
                    "--format=custom",
                    f"--file={temporary}",
                    f"--dbname={self._database}",
                ],
                env=self._postgres_environment(),
                check=True,
                capture_output=True,
                timeout=300,
            )
            if temporary.stat().st_size == 0:
                raise RuntimeError("pg_dump a produit une archive vide")
            os.replace(temporary, destination)
            self._prune_backups()
            return destination.name
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def restore_latest(self) -> str:
        backups = self._list_backups()
        if not backups:
            raise BackupUnavailable("aucune sauvegarde PostgreSQL disponible")

        archive = backups[0]
        env = self._postgres_environment()
        self._run(
            ["pg_restore", "--list", str(archive)],
            env=env,
            check=True,
            capture_output=True,
            timeout=30,
        )
        self._run(
            [
                "pg_restore",
                "--no-password",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--single-transaction",
                "--exit-on-error",
                f"--dbname={self._database}",
                str(archive),
            ],
            env=env,
            check=True,
            capture_output=True,
            timeout=300,
        )
        return archive.name

    def has_backups(self) -> bool:
        return bool(self._list_backups())

    def is_database_healthy(self) -> bool:
        result = self._run(
            [
                "pg_isready",
                "--quiet",
                "--host",
                self._pg_host,
                "--port",
                self._pg_port,
                "--username",
                self._pg_user,
                "--dbname",
                self._database,
            ],
            env=self._postgres_environment(),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return result.returncode == 0

    def _prune_backups(self) -> None:
        backups = self._list_backups()
        for old_backup in backups[self._retention :]:
            old_backup.unlink()

    def _list_backups(self) -> list[Path]:
        return sorted(
            (
                path
                for path in self._backup_dir.glob("backup-*.dump")
                if path.is_file() and not path.is_symlink()
            ),
            reverse=True,
        )

    def _postgres_environment(self) -> dict[str, str]:
        return {
            **os.environ,
            "PGHOST": self._pg_host,
            "PGPORT": self._pg_port,
            "PGUSER": self._pg_user,
            "PGPASSWORD": self._pg_password,
        }
