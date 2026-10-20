import subprocess
from pathlib import Path

import pytest

from app.adapters.postgres_archives import PostgresArchiveStore
from app.domain.ports import BackupUnavailable


def make_store(tmp_path: Path, runner=subprocess.run, retention=2):
    return (
        PostgresArchiveStore(
            "resilience",
            tmp_path,
            "postgres",
            5432,
            "resilience_owner",
            "db-secret",
            retention,
            run=runner,
        ),
        runner,
    )


def test_backup_is_atomic_and_password_is_not_a_command_argument(tmp_path):
    commands: list[tuple[list[str], dict[str, str]]] = []

    def runner(command, **kwargs):
        commands.append((command, kwargs["env"]))
        Path(command[3].removeprefix("--file=")).write_bytes(b"postgres archive")
        return subprocess.CompletedProcess(command, 0)

    store, _ = make_store(tmp_path, runner)
    name = store.create_backup()

    assert (tmp_path / name).read_bytes() == b"postgres archive"
    assert not list(tmp_path.glob(".backup-*.tmp"))
    assert commands[0][1]["PGPASSWORD"] == "db-secret"
    assert "db-secret" not in commands[0][0]


def test_backup_retention_removes_only_old_archives(tmp_path):
    def runner(command, **kwargs):
        Path(command[3].removeprefix("--file=")).write_bytes(b"archive")
        return subprocess.CompletedProcess(command, 0)

    store, _ = make_store(tmp_path, runner, retention=2)
    for _ in range(3):
        store.create_backup()

    assert len(list(tmp_path.glob("backup-*.dump"))) == 2


def test_restore_uses_most_recent_backup_and_validates_before_restore(tmp_path):
    older = tmp_path / "backup-20261020T100000.000000Z.dump"
    latest = tmp_path / "backup-20261020T110000.000000Z.dump"
    older.write_bytes(b"old")
    latest.write_bytes(b"new")
    commands: list[list[str]] = []

    def runner(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    store, _ = make_store(tmp_path, runner)
    assert store.restore_latest() == latest.name
    assert commands[0] == ["pg_restore", "--list", str(latest)]
    assert "--single-transaction" in commands[1]
    assert "--no-privileges" not in commands[1]
    assert commands[1][-1] == str(latest)


def test_restore_fails_clearly_when_no_backup_exists(tmp_path):
    store, _ = make_store(tmp_path)
    with pytest.raises(BackupUnavailable):
        store.restore_latest()


def test_readiness_requires_a_backup(tmp_path):
    store, _ = make_store(tmp_path)
    assert not store.has_backups()
    (tmp_path / "backup-20261020T110000.000000Z.dump").write_bytes(b"archive")
    assert store.has_backups()


def test_restore_skips_archives_taken_after_the_incident(tmp_path):
    from datetime import UTC, datetime

    good = tmp_path / "backup-20261020T100000.000000Z.dump"
    poisoned = tmp_path / "backup-20261020T110000.000000Z.dump"
    good.write_bytes(b"good")
    poisoned.write_bytes(b"corrupted")
    commands: list[list[str]] = []

    def runner(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    store, _ = make_store(tmp_path, runner)
    before = datetime(2026, 10, 20, 10, 30, tzinfo=UTC)
    assert store.restore_latest(before) == good.name
    assert commands[1][-1] == str(good)


def test_restore_fails_when_every_archive_is_newer_than_the_incident(tmp_path):
    from datetime import UTC, datetime

    (tmp_path / "backup-20261020T110000.000000Z.dump").write_bytes(b"late")
    store, _ = make_store(tmp_path)
    with pytest.raises(BackupUnavailable):
        store.restore_latest(datetime(2026, 10, 20, 10, 0, tzinfo=UTC))
