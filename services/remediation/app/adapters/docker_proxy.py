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
        restart_timeout_s: float = 30.0,
    ) -> None:
        self._client = client
        self._proxy_url = proxy_url.rstrip("/")
        self._container_names = container_names or {}
        # Docker laisse 10 s au conteneur pour s'arrêter avant de le tuer : plus que le délai
        # HTTP ordinaire, sinon un redémarrage réussi serait compté comme un échec.
        self._restart_timeout_s = restart_timeout_s

    def restart(self, service: str) -> None:
        container = self._container_names.get(service, service)
        response = self._client.post(
            f"{self._proxy_url}/containers/{container}/restart", timeout=self._restart_timeout_s
        )
        response.raise_for_status()
