"""Composition root : câble les adaptateurs aux ports (seul endroit qui les connaît)."""

from __future__ import annotations

import sys

import httpx
from fastapi import FastAPI

from app.adapters.api_probe import ApiTransactionProbe
from app.adapters.docker_proxy import DockerProxyClient
from app.adapters.http_health import HttpHealthChecker
from app.adapters.json_publisher import JsonStdoutPublisher
from app.api.routes import build_router
from app.application.actions import RestartServiceAction
from app.application.pipeline import RemediationPipeline
from app.application.policy import KindBasedPolicy
from app.application.verifier import HealthAndProbeVerifier
from app.config import Settings
from app.domain.models import Anomaly, IncidentKind


class _NoDetector:
    """Détection push : le détecteur ML appelle POST /incidents, aucun polling ici."""

    def detect(self) -> Anomaly | None:
        return None


def build_pipeline(settings: Settings, client: httpx.Client) -> RemediationPipeline:
    docker = DockerProxyClient(client, settings.docker_proxy_url, settings.container_names)
    # TODO(WAF, rotation de secrets) : ajouter BlockIpAction / RotateSecretAction dès que les
    # adaptateurs WafIpBlocker / VaultSecretRotator existent. Sans action, l'incident est
    # déclaré en échec (jamais « résolu » à tort).
    policy = KindBasedPolicy({IncidentKind.AVAILABILITY: [RestartServiceAction(docker)]})
    verifier = HealthAndProbeVerifier(
        HttpHealthChecker(client, {"api": settings.api_health_url}),
        ApiTransactionProbe(client, settings.api_base_url, settings.probe_token),
    )
    return RemediationPipeline(_NoDetector(), policy, verifier, JsonStdoutPublisher(sys.stdout))


def create_app(settings: Settings | None = None, client: httpx.Client | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    client = client or httpx.Client(timeout=settings.http_timeout_s)
    pipeline = build_pipeline(settings, client)
    app = FastAPI(title="remediation")
    app.include_router(build_router(lambda: pipeline, lambda: settings.ingest_token))
    return app
