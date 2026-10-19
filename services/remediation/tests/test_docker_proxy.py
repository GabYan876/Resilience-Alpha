import httpx
import pytest

from app.adapters.docker_proxy import DockerProxyClient


def make(handler, names=None) -> DockerProxyClient:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return DockerProxyClient(client, "http://docker-proxy:2375/", names)


def test_restart_calls_proxy_endpoint():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(204)

    make(handler, {"api": "ra-api-1"}).restart("api")
    assert seen[0].method == "POST"
    assert seen[0].url == "http://docker-proxy:2375/containers/ra-api-1/restart"


def test_restart_raises_when_proxy_refuses():
    with pytest.raises(httpx.HTTPStatusError):
        make(lambda r: httpx.Response(403)).restart("api")
