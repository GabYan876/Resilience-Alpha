"""Routes FastAPI : aucune logique métier, on délègue au pipeline injecté."""

from __future__ import annotations

import hmac
from collections.abc import Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.schemas import AnomalyIn, IncidentOut
from app.application.pipeline import RemediationPipeline
from app.domain.ports import IncidentStore


def build_router(
    get_pipeline: Callable[[], RemediationPipeline],
    get_ingest_token: Callable[[], str],
    get_store: Callable[[], IncidentStore],
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

    @router.get(
        "/incidents", response_model=list[IncidentOut], dependencies=[Depends(require_token)]
    )
    def list_incidents(
        limit: int = Query(default=50, ge=1, le=200),
        store: IncidentStore = Depends(get_store),
    ) -> list[IncidentOut]:
        return [IncidentOut.from_domain(i) for i in store.list_recent(limit)]

    @router.get(
        "/incidents/{incident_id}",
        response_model=IncidentOut,
        dependencies=[Depends(require_token)],
    )
    def get_incident(incident_id: str, store: IncidentStore = Depends(get_store)) -> IncidentOut:
        incident = store.get(incident_id)
        if incident is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "incident inconnu")
        return IncidentOut.from_domain(incident)

    return router
