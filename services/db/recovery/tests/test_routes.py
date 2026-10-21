from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.ports import IntegritySnapshot
from app.main import create_app


class FakeArchive:
    def create_backup(self) -> str:
        return "backup-test.dump"

    def restore_latest(self, before=None) -> str:
        self.before = before
        return "backup-test.dump"

    def is_database_healthy(self) -> bool:
        return True

    def has_backups(self) -> bool:
        return True


class FakeIntegrity:
    def snapshot(self) -> IntegritySnapshot:
        return IntegritySnapshot(transactions=4, ledger_entries=8, unbalanced_transactions=0)


def _settings():
    return Settings(
        database="resilience",
        backup_dir=Path("/tmp"),
        backup_interval_s=300,
        backup_retention=12,
        pg_host="postgres",
        pg_port=5432,
        pg_user="owner",
        pg_password="db-secret",
        probe_token="probe-secret",
    )


def make_client():
    return TestClient(create_app(_settings(), FakeArchive(), FakeIntegrity()))


def test_restore_requires_probe_token():
    with make_client() as client:
        assert client.post("/restore").status_code == 401
        assert client.post("/restore", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_restore_is_available_with_probe_token():
    with make_client() as client:
        response = client.post("/restore", headers={"Authorization": "Bearer probe-secret"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "archive": "backup-test.dump"}


def test_restore_forwards_the_incident_time_to_the_archive():
    archive = FakeArchive()
    client = TestClient(create_app(_settings(), archive))
    with client:
        response = client.post(
            "/restore",
            params={"before": "2026-10-20T10:30:00+00:00"},
            headers={"Authorization": "Bearer probe-secret"},
        )
    assert response.status_code == 200
    assert archive.before.isoformat() == "2026-10-20T10:30:00+00:00"


def test_integrity_exposes_counters_without_token():
    with make_client() as client:
        response = client.get("/integrity")
    assert response.status_code == 200
    assert response.json() == {
        "transactions": 4,
        "ledger_entries": 8,
        "unbalanced_transactions": 0,
    }
