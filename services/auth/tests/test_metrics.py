"""Composition root : `/metrics` doit répondre, sinon Prometheus voit `auth` en panne (up=0)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_metrics_endpoint_is_exposed() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/none", jwt_secret="x" * 32
    )
    client = TestClient(create_app(settings))

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text or "python_info" in response.text
