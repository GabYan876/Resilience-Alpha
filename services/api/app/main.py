"""Composition root : câble les adaptateurs aux ports (seul endroit qui les connaît)."""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.adapters.jwt_verifier import JwtTokenVerifier
from app.adapters.logging_publisher import JsonEventPublisher
from app.adapters.persistence.engine import build_engine, build_session_factory
from app.adapters.persistence.health import SqlAlchemyHealthProbe
from app.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from app.api.me_routes import build_me_router
from app.api.routes import build_router
from app.application.transfer import ExecuteTransfer
from app.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    engine = build_engine(
        settings.database_url, echo=settings.sql_echo, pool_size=settings.pool_size
    )
    session_factory = build_session_factory(engine)
    publisher = JsonEventPublisher(sys.stdout)

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    def transfer_factory() -> ExecuteTransfer:
        return ExecuteTransfer(uow_factory(), publisher)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        publisher.publish("service.started", trace_id="boot")
        yield
        await engine.dispose()  # un redémarrage propre libère les connexions

    app = FastAPI(title="api", lifespan=lifespan)
    app.include_router(
        build_router(
            uow_factory,
            transfer_factory,
            SqlAlchemyHealthProbe(engine),
            lambda: settings.probe_token,
        )
    )
    app.include_router(
        build_me_router(uow_factory, transfer_factory, JwtTokenVerifier(settings.jwt_secret))
    )
    # /metrics pour Prometheus ; /health et /metrics sont exclus des métriques de latence.
    Instrumentator(excluded_handlers=["/metrics", "/health"]).instrument(app).expose(
        app, endpoint="/metrics", include_in_schema=False
    )
    return app
