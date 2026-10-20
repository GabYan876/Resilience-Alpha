"""Composition root : câble les adaptateurs aux ports (seul endroit qui les connaît)."""

from __future__ import annotations

import sys

import httpx
from fastapi import FastAPI
from prometheus_client import CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator

from app.adapters.api_probe import ApiTransactionProbe
from app.adapters.docker_proxy import DockerProxyClient
from app.adapters.file_blocklist import BlocklistFile, IpBlocklist, SubjectBlocklist
from app.adapters.http_health import HttpHealthChecker
from app.adapters.json_publisher import JsonStdoutPublisher
from app.adapters.memory_store import InMemoryIncidentStore
from app.api.routes import build_router
from app.application.actions import BlockIpAction, BlockSubjectAction, RestartServiceAction
from app.application.pipeline import RemediationPipeline
from app.application.policy import KindBasedPolicy
from app.application.verifier import HealthAndProbeVerifier
from app.config import Settings
from app.domain.models import Anomaly, IncidentKind
from app.domain.ports import IncidentStore


class _NoDetector:
    """Détection push : le détecteur ML appelle POST /incidents, aucun polling ici."""

    def detect(self) -> Anomaly | None:
        return None


def build_pipeline(
    settings: Settings, client: httpx.Client, store: IncidentStore
) -> RemediationPipeline:
    docker = DockerProxyClient(
        client,
        settings.docker_proxy_url,
        settings.container_names,
        restart_timeout_s=settings.restart_timeout_s,
    )
    # TODO(rotation de secrets) : ajouter RotateSecretAction dès que VaultSecretRotator existe.
    blocklist = BlocklistFile(settings.blocklist_path)
    # Bloquer la source d'abord, puis redémarrer : sinon le flood reprend aussitôt. Une action
    # sans cible identifiée échoue sans empêcher les suivantes.
    policy = KindBasedPolicy(
        {
            IncidentKind.AVAILABILITY: [
                BlockIpAction(IpBlocklist(blocklist)),
                BlockSubjectAction(SubjectBlocklist(blocklist)),
                RestartServiceAction(docker),
            ]
        }
    )
    verifier = HealthAndProbeVerifier(
        HttpHealthChecker(client, {"api": settings.api_health_url}),
        ApiTransactionProbe(client, settings.api_base_url, settings.probe_token),
        health_wait_s=settings.verify_wait_s,
    )
    return RemediationPipeline(
        _NoDetector(), policy, verifier, JsonStdoutPublisher(sys.stdout), store=store
    )


def create_app(settings: Settings | None = None, client: httpx.Client | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    client = client or httpx.Client(timeout=settings.http_timeout_s)
    store = InMemoryIncidentStore()
    pipeline = build_pipeline(settings, client, store)
    app = FastAPI(title="remediation")
    app.include_router(build_router(lambda: pipeline, lambda: settings.ingest_token, lambda: store))
    # /metrics pour Prometheus ; /health et /metrics sont exclus des métriques de latence.
    # Registre propre à chaque app : le registre global lèverait des doublons à chaque create_app.
    Instrumentator(
        excluded_handlers=["/metrics", "/health"], registry=CollectorRegistry()
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    return app
