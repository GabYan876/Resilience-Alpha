import httpx

from app.cli.check_transaction import check_transaction
from app.config import Settings


def test_cli_runs_health_and_shared_transaction_probe():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/health":
            return httpx.Response(200)
        if request.url.path == "/transactions":
            return httpx.Response(201, json={"status": "settled"})
        return httpx.Response(404)

    settings = Settings(
        api_base_url="http://api:8000",
        api_health_url="http://api:8000/health",
        docker_proxy_url="http://docker-proxy:2375",
        ingest_token="ingest",
        probe_token="probe",
    )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert check_transaction(client, settings)

    assert [request.url.path for request in seen] == ["/health", "/transactions"]
    assert seen[1].headers["authorization"] == "Bearer probe"
    assert seen[1].read()
