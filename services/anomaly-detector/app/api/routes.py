"""Routes FastAPI : la détection tourne en tâche de fond, l'API n'expose que la santé."""

from __future__ import annotations

from fastapi import APIRouter


def build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return router
