"""LED bicolore de l'ESP32 : `POST /led` signé ; les durées sont gérées par le firmware."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Callable

import httpx

from app.domain.models import LedMode


class HttpStatusLed:
    """Requête signée (HMAC-SHA256 du compteur et du corps) : le secret ne circule pas.

    Le compteur croît strictement ; l'ESP32 refuse tout compteur déjà vu (rejeu).
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        secret: str,
        now_ms: Callable[[], int] = lambda: time.time_ns() // 1_000_000,
    ) -> None:
        self._client = client
        self._secret = secret.encode()
        self._now_ms = now_ms
        self._last_counter = 0

    async def set(self, mode: LedMode) -> None:
        self._last_counter = max(self._now_ms(), self._last_counter + 1)
        body = json.dumps({"mode": mode.value}, separators=(",", ":")).encode()
        signature = hmac.new(
            self._secret, f"{self._last_counter}.".encode() + body, hashlib.sha256
        ).hexdigest()
        response = await self._client.post(
            "/led",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Counter": str(self._last_counter),
                "X-Signature": signature,
            },
        )
        response.raise_for_status()


class NoStatusLed:
    """Pas d'ESP32 configuré : le retour visuel manque, l'accès n'en dépend pas."""

    async def set(self, mode: LedMode) -> None:
        return None
