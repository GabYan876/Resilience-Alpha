import httpx
import pytest

from app.adapters.db_integrity_source import HttpIntegritySource
from app.domain.models import IntegritySnapshot


def test_snapshot_reads_counters():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/integrity"
        return httpx.Response(
            200, json={"transactions": 4, "ledger_entries": 8, "unbalanced_transactions": 0}
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = HttpIntegritySource(client, "http://db-recovery:8001")
    assert source.snapshot() == IntegritySnapshot(4, 8, 0)


def test_snapshot_raises_when_service_unavailable():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503)))
    source = HttpIntegritySource(client, "http://db-recovery:8001")
    with pytest.raises(httpx.HTTPStatusError):
        source.snapshot()
