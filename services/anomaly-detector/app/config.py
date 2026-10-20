"""Lecture de la configuration et des secrets : seul endroit qui touche à l'environnement."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    prometheus_url: str
    remediation_url: str
    ingest_token: str  # jeton Bearer attendu par POST /incidents du moteur
    model_path: Path
    dataset_path: Path
    loki_url: str = "http://loki:3100"
    integrity_url: str = "http://db-recovery:8001"  # compteurs d'intégrité de la base
    # Attribution : un compte n'est désigné que s'il émet au moins `attacker_min_requests`
    # requêtes sur `attacker_window` ET au moins `attacker_min_share` du trafic identifié.
    # Sans cela, un utilisateur légitime serait bloqué à tort pendant un pic.
    attacker_window: str = "30s"
    attacker_min_requests: int = 100
    attacker_min_share: float = 0.5
    target_service: str = "api"
    poll_interval_s: float = 5.0
    confirmations: int = 3  # jugements anormaux consécutifs avant de signaler
    cooldown_s: float = 90.0  # silence après un signalement, le temps de la remédiation
    http_timeout_s: float = 3.0  # requêtes Prometheus : rapides
    # POST /incidents attend que le moteur ait fini (décision + action + vérification) avant
    # de répondre : il lui faut bien plus de temps qu'une requête Prometheus. Un timeout trop
    # court ferait croire à un échec de signalement alors que le moteur a bien agi, et
    # empêcherait le délai de grâce de s'enclencher (voir HttpAnomalyReporter).
    report_timeout_s: float = 75.0

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            prometheus_url=os.environ.get("PROMETHEUS_URL", "http://prometheus:9090"),
            remediation_url=os.environ.get("REMEDIATION_URL", "http://remediation:8000"),
            ingest_token=os.environ["REMEDIATION_INGEST_TOKEN"],
            model_path=Path(os.environ.get("MODEL_PATH", "/models/isolation_forest.joblib")),
            dataset_path=Path(os.environ.get("DATASET_PATH", "/data/normal.csv")),
            loki_url=os.environ.get("LOKI_URL", "http://loki:3100"),
            integrity_url=os.environ.get("INTEGRITY_URL", "http://db-recovery:8001"),
            attacker_window=os.environ.get("ATTACKER_WINDOW", "30s"),
            attacker_min_requests=int(os.environ.get("ATTACKER_MIN_REQUESTS", "100")),
            attacker_min_share=float(os.environ.get("ATTACKER_MIN_SHARE", "0.5")),
            target_service=os.environ.get("TARGET_SERVICE", "api"),
            poll_interval_s=float(os.environ.get("POLL_INTERVAL_S", "5")),
            confirmations=int(os.environ.get("CONFIRMATIONS", "3")),
            cooldown_s=float(os.environ.get("COOLDOWN_S", "90")),
            http_timeout_s=float(os.environ.get("HTTP_TIMEOUT_S", "3")),
            report_timeout_s=float(os.environ.get("REPORT_TIMEOUT_S", "75")),
        )
