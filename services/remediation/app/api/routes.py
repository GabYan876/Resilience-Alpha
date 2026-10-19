"""Routes FastAPI : aucune logique métier, on délègue au pipeline injecté."""

from __future__ import annotations

import hmac
from collections.abc import Callable

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.schemas import AnomalyIn, IncidentOut
from app.application.pipeline import RemediationPipeline


def build_router(
    get_pipeline: Callable[[], RemediationPipeline],
    get_ingest_token: Callable[[], str],
) -> APIRouter:
    router = APIRouter()

    def require_token(
        authorization: str = Header(default=""),
        expected: str = Depends(get_ingest_token),
    ) -> None:
        supplied = authorization.removeprefix("Bearer ")
        if not hmac.compare_digest(supplied, expected):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token invalide")

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.post("/incidents", response_model=IncidentOut, dependencies=[Depends(require_token)])
    def report_anomaly(
        body: AnomalyIn, pipeline: RemediationPipeline = Depends(get_pipeline)
    ) -> IncidentOut:
        return IncidentOut.from_domain(pipeline.handle(body.to_domain()))

    return router
