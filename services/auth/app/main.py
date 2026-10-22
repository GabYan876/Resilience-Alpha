"""Composition root : câble les adaptateurs aux ports (seul endroit qui les connaît)."""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.adapters.engine import SqlAlchemyHealthProbe, build_engine
from app.adapters.esp_led import HttpStatusLed, NoStatusLed
from app.adapters.host_agent import (
    HostAgentClient,
    HostCameraControl,
    HostFaceVerifier,
    UnconfiguredCamera,
    UnconfiguredFaceVerifier,
)
from app.adapters.logging_publisher import JsonEventPublisher
from app.adapters.memory_stores import (
    InMemoryAccessJournal,
    InMemoryFaceSessionStore,
    InMemoryLockoutStore,
    InMemoryRoleStore,
    SystemClock,
)
from app.adapters.security import Argon2PasswordHasher, JwtAdminTokens, JwtTokenIssuer
from app.adapters.sql_users import SqlUserRepository
from app.api.routes import build_admin_router, build_router
from app.application.backoffice_admin import BackOfficeAdmin
from app.application.backoffice_login import BackOfficeLogin
from app.application.use_cases import LoginUser, RegisterUser
from app.config import Settings
from app.domain.models import Role


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    engine = build_engine(settings.database_url)
    users = SqlUserRepository(engine)
    hasher = Argon2PasswordHasher()
    tokens = JwtTokenIssuer(settings.jwt_secret, settings.jwt_ttl_seconds)
    publisher = JsonEventPublisher(sys.stdout)

    # Agent caméra et ESP8266 : délais courts, la connexion ne doit pas rester suspendue.
    http_clients: list[httpx.AsyncClient] = []
    if settings.host_agent_url and settings.host_agent_token:
        agent_http = httpx.AsyncClient(base_url=settings.host_agent_url, timeout=15.0)
        http_clients.append(agent_http)
        agent = HostAgentClient(agent_http, settings.host_agent_token)
        camera, faces = HostCameraControl(agent), HostFaceVerifier(agent)
    else:  # échec fermé : sans agent, aucune connexion de back-office
        camera, faces = UnconfiguredCamera(), UnconfiguredFaceVerifier()
    if settings.led_url and settings.led_token:
        led_http = httpx.AsyncClient(base_url=settings.led_url, timeout=2.0)
        http_clients.append(led_http)
        led = HttpStatusLed(led_http, settings.led_token)
    else:
        led = NoStatusLed()
    admin_tokens = JwtAdminTokens(settings.jwt_secret, settings.admin_token_ttl_seconds)
    lockouts = InMemoryLockoutStore()
    roles = InMemoryRoleStore({identifier: Role.ADMIN for identifier in settings.backoffice_admins})
    journal = InMemoryAccessJournal()
    clock = SystemClock()
    backoffice = BackOfficeLogin(
        users,
        hasher,
        admin_tokens,
        camera,
        faces,
        led,
        lockouts,
        InMemoryFaceSessionStore(),
        clock,
        publisher,
        roles,
        journal,
    )
    backoffice_admin = BackOfficeAdmin(users, roles, lockouts, journal, clock, publisher)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        publisher.publish("service.started", trace_id="boot")
        yield
        for http_client in http_clients:
            await http_client.aclose()
        await engine.dispose()

    app = FastAPI(title="auth", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.include_router(
        build_router(
            lambda: RegisterUser(users, hasher, tokens, publisher, settings.welcome_balance_cents),
            lambda: LoginUser(users, hasher, tokens, publisher),
            SqlAlchemyHealthProbe(engine),
        )
    )

    app.include_router(
        build_admin_router(lambda: backoffice, lambda: backoffice_admin, admin_tokens)
    )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Contrat du front : un corps { "error": "..." } lisible, jamais l'écho de la saisie.
        errors = exc.errors()
        field = ".".join(str(p) for p in errors[0]["loc"][1:]) if errors else "requête"
        return JSONResponse({"error": f"champ invalide : {field}"}, status_code=422)

    # /metrics pour Prometheus (panneau « Santé des services ») ; /health et /metrics exclus.
    Instrumentator(excluded_handlers=["/metrics", "/health"]).instrument(app).expose(
        app, endpoint="/metrics", include_in_schema=False
    )
    return app
