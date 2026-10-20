"""Routes FastAPI : aucune logique métier, on délègue aux cas d'usage injectés."""

from __future__ import annotations

import hmac
import uuid
from collections.abc import Callable

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.schemas import AskIn, AskOut
from app.application.ask import AskService
from app.application.indexing import IndexingService
from app.domain.models import AssistantUnavailable, InvalidQuestion


def build_router(
    get_ask: Callable[[], AskService],
    get_indexing: Callable[[], IndexingService],
    get_token: Callable[[], str],
) -> APIRouter:
    router = APIRouter()

    def require_token(
        authorization: str = Header(default=""),
        expected: str = Depends(get_token),
    ) -> None:
        supplied = authorization.removeprefix("Bearer ")
        if not hmac.compare_digest(supplied, expected):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token invalide")

    @router.get("/health")
    def health(indexing: IndexingService = Depends(get_indexing)) -> dict[str, object]:
        return {"status": "ok", "indexed_chunks": indexing.chunk_count}

    @router.post("/ask", response_model=AskOut, dependencies=[Depends(require_token)])
    def ask(body: AskIn, service: AskService = Depends(get_ask)) -> AskOut:
        trace_id = uuid.uuid4().hex
        try:
            return AskOut.from_domain(service.ask(body.question, trace_id), trace_id)
        except InvalidQuestion as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
        except AssistantUnavailable as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    @router.post("/reindex", dependencies=[Depends(require_token)])
    def reindex(indexing: IndexingService = Depends(get_indexing)) -> dict[str, int]:
        try:
            return {"chunks": indexing.reindex(uuid.uuid4().hex)}
        except AssistantUnavailable as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    return router
