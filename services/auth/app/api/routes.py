"""Routes FastAPI : traduction HTTP <-> cas d'usage, aucune logique métier."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.schemas import AuthOut, LoginIn, RegisterIn
from app.application.use_cases import LoginUser, RegisterUser
from app.domain.errors import EmailAlreadyUsed, InvalidCredentials, PhoneAlreadyUsed
from app.domain.ports import HealthProbe


def build_router(
    register_factory: Callable[[], RegisterUser],
    login_factory: Callable[[], LoginUser],
    health_probe: HealthProbe,
) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health(response: Response) -> dict[str, str]:
        if not await health_probe.ping():
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "degraded", "database": "down"}
        return {"status": "ok", "database": "up"}

    @router.post("/auth/register", response_model=AuthOut, response_model_by_alias=True)
    async def register(
        body: RegisterIn, use_case: RegisterUser = Depends(register_factory)
    ) -> AuthOut:
        try:
            result = await use_case.execute(
                full_name=body.name, email=body.email, phone=body.number, password=body.password
            )
        except (EmailAlreadyUsed, PhoneAlreadyUsed) as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
        return AuthOut.from_result(result)

    @router.post("/auth/login", response_model=AuthOut, response_model_by_alias=True)
    async def login(body: LoginIn, use_case: LoginUser = Depends(login_factory)) -> AuthOut:
        try:
            result = await use_case.execute(email=body.email, password=body.password)
        except InvalidCredentials as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
        return AuthOut.from_result(result)

    return router
