"""Clients de l'agent hôte et de la LED : transport HTTP simulé, échec fermé."""

from __future__ import annotations

import httpx
import pytest

from app.adapters.esp_led import HttpStatusLed
from app.adapters.host_agent import HostAgentClient, HostCameraControl, HostFaceVerifier
from app.domain.errors import FaceCheckUnavailable
from app.domain.models import LedMode


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url="http://agent", transport=httpx.MockTransport(handler))


@pytest.mark.anyio
async def test_verify_envoie_le_jeton_et_lit_la_correspondance() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"match": True})

    verifier = HostFaceVerifier(HostAgentClient(_client(handler), "jeton"))

    assert await verifier.verify("a@b.fr") is True
    assert seen[0].headers["Authorization"] == "Bearer jeton"
    assert seen[0].url.path == "/verify"


@pytest.mark.anyio
async def test_verify_faux_si_pas_de_correspondance() -> None:
    client = _client(lambda r: httpx.Response(200, json={"match": False}))

    assert await HostFaceVerifier(HostAgentClient(client, "t")).verify("a@b.fr") is False


@pytest.mark.anyio
@pytest.mark.parametrize(
    "handler",
    [
        lambda r: httpx.Response(500),
        lambda r: httpx.Response(200, text="pas du json"),
        lambda r: (_ for _ in ()).throw(httpx.ConnectError("hors ligne")),
    ],
)
async def test_panne_de_l_agent_devient_face_check_unavailable(handler) -> None:
    agent = HostAgentClient(_client(handler), "t")

    with pytest.raises(FaceCheckUnavailable):
        await HostCameraControl(agent).start()
    with pytest.raises(FaceCheckUnavailable):
        await HostFaceVerifier(agent).verify("a@b.fr")


@pytest.mark.anyio
async def test_led_poste_le_mode_avec_le_jeton() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200)

    await HttpStatusLed(_client(handler), "jeton-led").set(LedMode.RED_BLINK)

    assert seen[0].url.path == "/led"
    assert seen[0].read() == b'{"mode":"red_blink"}'
    assert seen[0].headers["Authorization"] == "Bearer jeton-led"
