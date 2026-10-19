"""Composition root : câble les adaptateurs aux ports (seul endroit qui les connaît)."""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.adapters.engine import SqlAlchemyHealthProbe, build_engine
from app.adapters.logging_publisher import JsonEventPublisher
from app.adapters.security import Argon2PasswordHasher, JwtTokenIssuer
from app.adapters.sql_users import SqlUserRepository
from app.api.routes import build_router
from app.application.use_cases import LoginUser, RegisterUser
from app.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    engine = build_engine(settings.database_url)
    users = SqlUserRepository(engine)
    hasher = Argon2PasswordHasher()
    tokens = JwtTokenIssuer(settings.jwt_secret, settings.jwt_ttl_seconds)
    publisher = JsonEventPublisher(sys.stdout)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        publisher.publish("service.started", trace_id="boot")
        yield
        await engine.dispose()

    app = FastAPI(title="auth", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.include_router(
        build_router(
            lambda: RegisterUser(users, hasher, tokens, publisher, settings.welcome_balance_cents),
            lambda: LoginUser(users, hasher, tokens, publisher),
            SqlAlchemyHealthProbe(engine),
        )
    )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Contrat du front : un corps { "error": "..." } lisible, jamais l'écho de la saisie.
        errors = exc.errors()
        field = ".".join(str(p) for p in errors[0]["loc"][1:]) if errors else "requête"
        return JSONResponse({"error": f"champ invalide : {field}"}, status_code=422)

    return app
