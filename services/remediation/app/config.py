"""Lecture de la configuration et des secrets : seul endroit qui touche à l'environnement."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

DEFAULT_CONTAINER_NAMES = {"api": "resilience-api"}


def parse_container_names(raw: str) -> dict[str, str]:
    """Lit `service=conteneur,service=conteneur` ; vide = valeurs par défaut."""
    if not raw.strip():
        return dict(DEFAULT_CONTAINER_NAMES)
    pairs = (item.split("=", 1) for item in raw.split(",") if item.strip())
    return {service.strip(): container.strip() for service, container in pairs}


@dataclass(frozen=True)
class Settings:
    api_base_url: str
    api_health_url: str
    docker_proxy_url: str
    ingest_token: str  # protège POST /incidents (appelé par le détecteur)
    probe_token: str  # jeton du compte de test utilisé par la sonde de transaction
    database_recovery_url: str = "http://db-recovery:8001"
    restore_safety_margin_s: float = 60.0  # écart détection/corruption exclu de la restauration
    blocklist_path: str = "/blocklist/blocked.txt"  # liste lue par le WAF (volume partagé)
    http_timeout_s: float = 3.0
    restart_timeout_s: float = 30.0  # délai de la requête de redémarrage Docker
    verify_wait_s: float = 30.0  # temps laissé à l'API pour redevenir saine avant de conclure
    watch_interval_s: float = 0.0  # sondage de santé (détection de crash) ; 0 = désactivé
    watch_failures: int = 3  # sondages consécutifs en échec avant de déclarer une panne
    # Service Compose -> nom réel du conteneur (`container_name`) que Docker accepte dans l'URL.
    container_names: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType(dict(DEFAULT_CONTAINER_NAMES))
    )

    @classmethod
    def from_env(cls) -> Settings:
        api_base_url = os.environ.get("API_BASE_URL", "http://api:8000")
        return cls(
            api_base_url=api_base_url,
            api_health_url=os.environ.get("API_HEALTH_URL", f"{api_base_url}/health"),
            docker_proxy_url=os.environ.get("DOCKER_PROXY_URL", "http://docker-proxy-ctl:2375"),
            database_recovery_url=os.environ.get(
                "DATABASE_RECOVERY_URL", "http://db-recovery:8001"
            ),
            restore_safety_margin_s=float(os.environ.get("DB_RESTORE_SAFETY_MARGIN_S", "60")),
            ingest_token=os.environ["REMEDIATION_INGEST_TOKEN"],
            probe_token=os.environ.get("PROBE_TOKEN", ""),
            blocklist_path=os.environ.get("WAF_BLOCKLIST_PATH", "/blocklist/blocked.txt"),
            http_timeout_s=float(os.environ.get("HTTP_TIMEOUT_S", "3")),
            restart_timeout_s=float(os.environ.get("RESTART_TIMEOUT_S", "30")),
            verify_wait_s=float(os.environ.get("VERIFY_WAIT_S", "30")),
            watch_interval_s=float(os.environ.get("WATCH_INTERVAL_S", "5")),
            watch_failures=int(os.environ.get("WATCH_FAILURES", "3")),
            container_names=parse_container_names(os.environ.get("CONTAINER_NAMES", "")),
        )
