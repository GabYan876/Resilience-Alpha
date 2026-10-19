"""Lecture de la configuration et des secrets : seul endroit qui touche à l'environnement."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_base_url: str
    api_health_url: str
    docker_proxy_url: str
    ingest_token: str  # protège POST /incidents (appelé par le détecteur)
    probe_token: str  # jeton du compte de test utilisé par la sonde de transaction
    http_timeout_s: float = 3.0

    @classmethod
    def from_env(cls) -> Settings:
        api_base_url = os.environ.get("API_BASE_URL", "http://api:8000")
        return cls(
            api_base_url=api_base_url,
            api_health_url=os.environ.get("API_HEALTH_URL", f"{api_base_url}/health"),
            docker_proxy_url=os.environ.get("DOCKER_PROXY_URL", "http://docker-proxy:2375"),
            ingest_token=os.environ["REMEDIATION_INGEST_TOKEN"],
            probe_token=os.environ.get("PROBE_TOKEN", ""),
            http_timeout_s=float(os.environ.get("HTTP_TIMEOUT_S", "3")),
        )
