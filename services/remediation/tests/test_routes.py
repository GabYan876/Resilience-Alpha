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
    if request.url.path == "/transactions":
        return httpx.Response(201, json={"status": "settled"})
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


AUTH = {"Authorization": f"Bearer {TOKEN}"}


def test_list_incidents_requires_token():
    assert make_client(ok_handler).get("/incidents").status_code == 401


def test_list_incidents_is_empty_at_start():
    assert make_client(ok_handler).get("/incidents", headers=AUTH).json() == []


def test_list_incidents_returns_newest_first_with_context():
    client = make_client(ok_handler)
    first = client.post("/incidents", json=FLOOD, headers=AUTH).json()
    second = client.post("/incidents", json={**FLOOD, "kind": "compromise"}, headers=AUTH).json()
    listed = client.get("/incidents", headers=AUTH).json()
    assert [i["id"] for i in listed] == [second["id"], first["id"]]
    assert listed[1]["status"] == "resolved"
    assert listed[0]["status"] == "failed"
    assert listed[1]["attacker_ip"] == "192.168.137.50"
    assert listed[1]["target_service"] == "api"
    assert "started_at" in listed[1]


def test_list_incidents_honours_limit():
    client = make_client(ok_handler)
    for _ in range(3):
        client.post("/incidents", json=FLOOD, headers=AUTH)
    assert len(client.get("/incidents?limit=2", headers=AUTH).json()) == 2
    assert client.get("/incidents?limit=0", headers=AUTH).status_code == 422


def test_get_incident_by_id_and_unknown():
    client = make_client(ok_handler)
    created = client.post("/incidents", json=FLOOD, headers=AUTH).json()
    assert client.get(f"/incidents/{created['id']}", headers=AUTH).json()["id"] == created["id"]
    assert client.get("/incidents/inconnu", headers=AUTH).status_code == 404


def test_metrics_exposes_prometheus_counters_without_token():
    client = make_client(ok_handler)
    client.post("/incidents", json=FLOOD, headers=AUTH)
    body = client.get("/metrics").text
    assert "http_requests_total" in body
    assert 'handler="/incidents"' in body
