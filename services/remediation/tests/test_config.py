import httpx
import pytest

from app.adapters.docker_proxy import DockerProxyClient
from app.adapters.memory_store import InMemoryIncidentStore
from app.config import DEFAULT_CONTAINER_NAMES, Settings, parse_container_names
from app.main import build_pipeline


def test_default_container_name_matches_compose_container_name():
    assert parse_container_names("") == DEFAULT_CONTAINER_NAMES
    assert DEFAULT_CONTAINER_NAMES["api"] == "resilience-api"


def test_parse_container_names_overrides_and_trims():
    assert parse_container_names("api = ra-api , auth=ra-auth") == {
        "api": "ra-api",
        "auth": "ra-auth",
    }


def test_from_env_requires_ingest_token(monkeypatch):
    monkeypatch.delenv("REMEDIATION_INGEST_TOKEN", raising=False)
    with pytest.raises(KeyError):
        Settings.from_env()


def test_from_env_reads_container_names(monkeypatch):
    monkeypatch.setenv("REMEDIATION_INGEST_TOKEN", "t")
    monkeypatch.setenv("CONTAINER_NAMES", "api=ra-api")
    assert Settings.from_env().container_names == {"api": "ra-api"}


def test_pipeline_restarts_the_compose_container_name():
    import httpx

    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(204 if request.method == "POST" else 200, json={})

    settings = Settings(
        api_base_url="http://api:8000",
        api_health_url="http://api:8000/health",
        docker_proxy_url="http://docker-proxy:2375",
        ingest_token="t",
        probe_token="",
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))
    pipeline = build_pipeline(settings, client, InMemoryIncidentStore())

    from app.domain.models import Anomaly, IncidentKind

    pipeline.handle(
        Anomaly(
            score=1.0,
            source="test",
            kind_hint=IncidentKind.AVAILABILITY,
            target_service="api",
        )
    )
    assert "http://docker-proxy:2375/containers/resilience-api/restart" in seen


def test_restart_request_uses_its_own_longer_timeout():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["timeout"] = request.extensions["timeout"]
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(handler), timeout=3.0)
    DockerProxyClient(client, "http://proxy", restart_timeout_s=30.0).restart("api")
    assert seen["timeout"]["read"] == 30.0
