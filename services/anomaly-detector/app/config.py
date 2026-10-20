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
    target_service: str = "api"
    poll_interval_s: float = 5.0
    confirmations: int = 3  # jugements anormaux consécutifs avant de signaler
    cooldown_s: float = 90.0  # silence après un signalement, le temps de la remédiation
    http_timeout_s: float = 3.0

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            prometheus_url=os.environ.get("PROMETHEUS_URL", "http://prometheus:9090"),
            remediation_url=os.environ.get("REMEDIATION_URL", "http://remediation:8000"),
            ingest_token=os.environ["REMEDIATION_INGEST_TOKEN"],
            model_path=Path(os.environ.get("MODEL_PATH", "/models/isolation_forest.joblib")),
            dataset_path=Path(os.environ.get("DATASET_PATH", "/data/normal.csv")),
            target_service=os.environ.get("TARGET_SERVICE", "api"),
            poll_interval_s=float(os.environ.get("POLL_INTERVAL_S", "5")),
            confirmations=int(os.environ.get("CONFIRMATIONS", "3")),
            cooldown_s=float(os.environ.get("COOLDOWN_S", "90")),
            http_timeout_s=float(os.environ.get("HTTP_TIMEOUT_S", "3")),
        )
