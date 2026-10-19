"""Client Docker passant par le docker-socket-proxy (jamais d'accès direct à docker.sock).

Le proxy n'expose que les endpoints autorisés (ici : redémarrage de conteneur).
"""

from __future__ import annotations

from collections.abc import Mapping

import httpx


class DockerProxyClient:
    def __init__(
        self,
        client: httpx.Client,
        proxy_url: str,
        container_names: Mapping[str, str] | None = None,
    ) -> None:
        self._client = client
        self._proxy_url = proxy_url.rstrip("/")
        self._container_names = container_names or {}

    def restart(self, service: str) -> None:
        container = self._container_names.get(service, service)
        response = self._client.post(f"{self._proxy_url}/containers/{container}/restart")
        response.raise_for_status()
