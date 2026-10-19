import httpx

from app.adapters.http_health import HttpHealthChecker


def checker(handler) -> HttpHealthChecker:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpHealthChecker(client, {"api": "http://api/health"})


def test_healthy_on_2xx():
    assert checker(lambda r: httpx.Response(200)).is_healthy("api")


def test_unhealthy_on_5xx():
    assert not checker(lambda r: httpx.Response(503)).is_healthy("api")


def test_unhealthy_on_connection_error():
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    assert not checker(boom).is_healthy("api")


def test_unknown_service_is_unhealthy():
    assert not checker(lambda r: httpx.Response(200)).is_healthy("inconnu")
