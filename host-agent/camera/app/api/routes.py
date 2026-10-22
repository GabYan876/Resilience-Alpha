"""Routes de l'agent : traduction HTTP <-> cas d'usage, jeton obligatoire, aucune logique métier."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.application.face_agent import FaceAgent
from app.domain.errors import CameraError


class VerifyIn(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)


def build_router(agent: FaceAgent, token: str) -> APIRouter:
    def require_token(authorization: str = Header(default="")) -> None:
        expected = f"Bearer {token}"
        if not hmac.compare_digest(authorization.encode(), expected.encode()):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "jeton invalide")

    router = APIRouter(dependencies=[Depends(require_token)])

    @router.post("/camera/start")
    def start() -> dict[str, str]:
        try:
            agent.start()
        except CameraError as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
        return {"status": "on"}

    @router.post("/camera/stop")
    def stop() -> dict[str, str]:
        agent.stop()
        return {"status": "off"}

    @router.post("/verify")
    def verify(body: VerifyIn) -> dict[str, bool]:
        try:
            return {"match": agent.verify(body.identifier)}
        except CameraError as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    return router
