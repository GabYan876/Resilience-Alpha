"""Routes FastAPI : traduction HTTP <-> cas d'usage, aucune logique métier."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.schemas import AdminIdentifyIn, AdminLoginIn, AuthOut, LoginIn, RegisterIn
from app.application.backoffice_login import BackOfficeLogin
from app.application.use_cases import LoginUser, RegisterUser
from app.domain.errors import (
    AccountLocked,
    EmailAlreadyUsed,
    FaceCheckUnavailable,
    FaceNotRecognized,
    FaceNotVerified,
    InvalidCredentials,
    PhoneAlreadyUsed,
)
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


def build_admin_router(backoffice_factory: Callable[[], BackOfficeLogin]) -> APIRouter:
    """Connexion du back-office en deux étapes : visage (caméra de l'hôte) puis mot de passe."""
    router = APIRouter(prefix="/auth/admin")

    @router.post("/identify")
    async def identify(
        body: AdminIdentifyIn, use_case: BackOfficeLogin = Depends(backoffice_factory)
    ) -> dict[str, str]:
        try:
            await use_case.start(body.identifier)
        except AccountLocked as exc:
            raise _locked(exc) from exc
        except FaceNotRecognized as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
        except FaceCheckUnavailable as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
        return {"status": "face_recognized"}

    @router.post("/login", response_model=AuthOut, response_model_by_alias=True)
    async def login(
        body: AdminLoginIn, use_case: BackOfficeLogin = Depends(backoffice_factory)
    ) -> AuthOut:
        try:
            result = await use_case.submit_password(body.identifier, body.password)
        except AccountLocked as exc:
            raise _locked(exc) from exc
        except FaceNotVerified as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
        except InvalidCredentials as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
        return AuthOut.from_result(result)

    return router


def _locked(exc: AccountLocked) -> HTTPException:
    return HTTPException(
        status.HTTP_423_LOCKED, str(exc), headers={"Retry-After": str(exc.retry_after_seconds)}
    )
