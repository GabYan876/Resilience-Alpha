"""Clients HTTP de l'agent hôte (caméra USB + reconnaissance, hors Docker). Échec fermé."""

from __future__ import annotations

import httpx

from app.domain.errors import FaceCheckUnavailable


class HostAgentClient:
    """Appels JSON authentifiés par jeton ; toute panne devient `FaceCheckUnavailable`."""

    def __init__(self, client: httpx.AsyncClient, token: str) -> None:
        self._client = client
        self._headers = {"Authorization": f"Bearer {token}"}

    async def post(self, path: str, **payload: object) -> dict[str, object]:
        try:
            response = await self._client.post(path, json=payload, headers=self._headers)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise FaceCheckUnavailable("agent hôte indisponible") from exc
        return body if isinstance(body, dict) else {}


class HostCameraControl:
    def __init__(self, agent: HostAgentClient) -> None:
        self._agent = agent

    async def start(self) -> None:
        await self._agent.post("/camera/start")

    async def stop(self) -> None:
        await self._agent.post("/camera/stop")


class HostFaceVerifier:
    def __init__(self, agent: HostAgentClient) -> None:
        self._agent = agent

    async def verify(self, identifier: str) -> bool:
        body = await self._agent.post("/verify", identifier=identifier)
        return body.get("match") is True


class UnconfiguredCamera:
    """Aucun agent configuré : la connexion du back-office reste fermée."""

    async def start(self) -> None:
        raise FaceCheckUnavailable("agent hôte non configuré")

    async def stop(self) -> None:
        return None


class UnconfiguredFaceVerifier:
    async def verify(self, identifier: str) -> bool:
        raise FaceCheckUnavailable("agent hôte non configuré")
