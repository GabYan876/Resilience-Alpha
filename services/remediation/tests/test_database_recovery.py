from datetime import UTC, datetime

import httpx
import pytest

from app.adapters.database_recovery import HttpDatabaseRestorer

INCIDENT_TIME = datetime(2026, 10, 20, 10, 30, tzinfo=UTC)


def test_restore_uses_probe_token():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    HttpDatabaseRestorer(client, "http://db-recovery:8001/", "probe-secret").restore_latest(INCIDENT_TIME)
    assert seen[0].url == "http://db-recovery:8001/restore"
    assert seen[0].headers["authorization"] == "Bearer probe-secret"
    assert seen[0].url.params["before"] == "2026-10-20T10:30:00+00:00"


def test_restore_surfaces_service_failure():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503)))
    with pytest.raises(httpx.HTTPStatusError):
        HttpDatabaseRestorer(client, "http://db-recovery:8001", "probe-secret").restore_latest(INCIDENT_TIME)
