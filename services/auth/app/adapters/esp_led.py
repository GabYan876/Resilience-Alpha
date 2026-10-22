"""LED bicolore de l'ESP8266 : `POST /led` avec jeton ; les durées sont gérées par le firmware."""

from __future__ import annotations

import httpx

from app.domain.models import LedMode


class HttpStatusLed:
    def __init__(self, client: httpx.AsyncClient, token: str) -> None:
        self._client = client
        self._headers = {"Authorization": f"Bearer {token}"}

    async def set(self, mode: LedMode) -> None:
        response = await self._client.post("/led", json={"mode": mode.value}, headers=self._headers)
        response.raise_for_status()


class NoStatusLed:
    """Pas d'ESP8266 configuré : le retour visuel manque, l'accès n'en dépend pas."""

    async def set(self, mode: LedMode) -> None:
        return None
