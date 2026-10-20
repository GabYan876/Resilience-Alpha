"""Composition root : câble les adaptateurs aux ports (seul endroit qui les connaît)."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from prometheus_client import CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator

from app.adapters.http_reporter import HttpAnomalyReporter
from app.adapters.isolation_forest import JoblibModelStore
from app.adapters.prometheus_observer import PrometheusVerdictObserver
from app.adapters.prometheus_source import PrometheusMetricsSource
from app.api.routes import build_router
from app.application.detection import DetectionService
from app.config import Settings
from app.logging_json import configure_logging

log = logging.getLogger("detector")


def build_service(
    settings: Settings, client: httpx.Client, registry: CollectorRegistry
) -> DetectionService:
    return DetectionService(
        PrometheusMetricsSource(client, settings.prometheus_url, settings.target_service),
        JoblibModelStore(settings.model_path).load(),
        HttpAnomalyReporter(client, settings.remediation_url, settings.ingest_token),
        target_service=settings.target_service,
        confirmations=settings.confirmations,
        cooldown_s=settings.cooldown_s,
        clock=time.monotonic,
        observers=[PrometheusVerdictObserver(registry)],
    )


async def _watch(service: DetectionService, interval_s: float) -> None:
    while True:
        detection = await asyncio.to_thread(service.tick)
        if detection is not None:
            log.warning(
                "anomalie signalée au moteur de remédiation",
                extra={
                    "event": "anomaly.reported",
                    "score": detection.score,
                    "target_service": detection.target_service,
                    "kind": detection.kind.value,
                },
            )
        await asyncio.sleep(interval_s)


def create_app(settings: Settings | None = None, client: httpx.Client | None = None) -> FastAPI:
    configure_logging()
    settings = settings or Settings.from_env()
    client = client or httpx.Client(timeout=settings.http_timeout_s)
    registry = CollectorRegistry()
    service = build_service(settings, client, registry)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        task = asyncio.create_task(_watch(service, settings.poll_interval_s))
        yield
        task.cancel()

    app = FastAPI(title="anomaly-detector", lifespan=lifespan)
    app.include_router(build_router())
    Instrumentator(excluded_handlers=["/metrics", "/health"], registry=registry).instrument(
        app
    ).expose(app, endpoint="/metrics", include_in_schema=False)
    return app
