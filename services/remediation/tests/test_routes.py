import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

TOKEN = "test-token"  # placeholder de test, pas un vrai secret


def make_client(handler) -> TestClient:
    settings = Settings(
        api_base_url="http://api",
        api_health_url="http://api/health",
        docker_proxy_url="http://proxy",
        ingest_token=TOKEN,
        probe_token="",
    )
    http = httpx.Client(transport=httpx.MockTransport(handler))
    app = create_app(settings, http)  # même câblage que la prod, transport HTTP simulé
    return TestClient(app)


FLOOD = {"score": 0.9, "source": "test", "kind": "availability", "attacker_ip": "192.168.137.50"}


def ok_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200)


def test_health_is_open():
    assert make_client(ok_handler).get("/health").json() == {"status": "ok"}


def test_incidents_requires_token():
    client = make_client(ok_handler)
    assert client.post("/incidents", json=FLOOD).status_code == 401
    bad = client.post("/incidents", json=FLOOD, headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401


def test_flood_incident_is_resolved_after_restart_and_transaction():
    response = make_client(ok_handler).post(
        "/incidents", json=FLOOD, headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


def test_compromise_without_adapter_is_failed_not_resolved():
    body = {**FLOOD, "kind": "compromise"}
    response = make_client(ok_handler).post(
        "/incidents", json=body, headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert response.json()["status"] == "failed"
