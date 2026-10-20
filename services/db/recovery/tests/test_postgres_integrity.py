import subprocess

import pytest

from app.adapters.postgres_integrity import PostgresIntegrityProbe
from app.domain.ports import IntegritySnapshot


def _probe(stdout: str = "4,8,0" + chr(10), error: Exception | None = None):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if error:
            raise error
        return subprocess.CompletedProcess(command, 0, stdout=stdout)

    return PostgresIntegrityProbe("resilience", "postgres", 5432, "owner", "db-secret", run), calls


def test_snapshot_parses_counters():
    probe, calls = _probe()
    assert probe.snapshot() == IntegritySnapshot(4, 8, 0)
    command, kwargs = calls[0]
    assert command[0] == "psql"
    assert kwargs["env"]["PGPASSWORD"] == "db-secret"
    assert "db-secret" not in " ".join(command)


def test_snapshot_propagates_psql_failure():
    probe, _ = _probe(error=subprocess.CalledProcessError(2, "psql"))
    with pytest.raises(subprocess.CalledProcessError):
        probe.snapshot()


def test_snapshot_rejects_unexpected_output():
    probe, _ = _probe(stdout="oups")
    with pytest.raises(ValueError):
        probe.snapshot()
