"""Routes FastAPI : traduction HTTP <-> cas d'usage, aucune logique métier."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.api.schemas import (
    AccessEntryOut,
    AdminIdentifyIn,
    AdminLoginIn,
    AdminSessionOut,
    AuthOut,
    HabilitationIn,
    HabilitationOut,
    LockoutOut,
    LoginIn,
    RegisterIn,
)
from app.application.backoffice_admin import BackOfficeAdmin
from app.application.backoffice_login import BackOfficeLogin
from app.application.use_cases import LoginUser, RegisterUser
from app.domain.errors import (
    AccountLocked,
    CannotRevokeSelf,
    EmailAlreadyUsed,
    FaceCheckUnavailable,
    FaceNotRecognized,
    FaceNotVerified,
    InvalidCredentials,
    NotAuthorized,
    PhoneAlreadyUsed,
    UnknownUser,
)
from app.domain.models import Role
from app.domain.ports import AdminTokenVerifier, HealthProbe

T = TypeVar("T")


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


def build_admin_router(
    backoffice_factory: Callable[[], BackOfficeLogin],
    admin_factory: Callable[[], BackOfficeAdmin],
    admin_tokens: AdminTokenVerifier,
) -> APIRouter:
    """Back-office : connexion en deux étapes (visage puis mot de passe), puis administration."""
    router = APIRouter(prefix="/auth/admin")

    def current_admin(authorization: str = Header(default="")) -> str:
        scheme, _, token = authorization.partition(" ")
        identifier = admin_tokens.verify_admin(token) if scheme.lower() == "bearer" else None
        if identifier is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session de back-office requise")
        return identifier

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

    @router.post("/login", response_model=AdminSessionOut)
    async def login(
        body: AdminLoginIn, use_case: BackOfficeLogin = Depends(backoffice_factory)
    ) -> AdminSessionOut:
        try:
            session = await use_case.submit_password(body.identifier, body.password)
        except AccountLocked as exc:
            raise _locked(exc) from exc
        except FaceNotVerified as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
        except NotAuthorized as exc:
            # Corps distinct du 403 « visage » : le front ne renvoie pas vers la caméra.
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, {"error": str(exc), "reason": "no_role"}
            ) from exc
        except InvalidCredentials as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
        return AdminSessionOut.from_session(session)

    @router.get("/me")
    async def me(
        actor: str = Depends(current_admin), use_case: BackOfficeAdmin = Depends(admin_factory)
    ) -> HabilitationOut:
        role = await _admin_call(use_case.whoami(actor))
        return HabilitationOut(identifier=actor, role=role.value)

    @router.get("/habilitations")
    async def habilitations(
        actor: str = Depends(current_admin), use_case: BackOfficeAdmin = Depends(admin_factory)
    ) -> list[HabilitationOut]:
        items = await _admin_call(use_case.habilitations(actor))
        return [HabilitationOut(identifier=h.identifier, role=h.role.value) for h in items]

    # POST seulement (pas de PUT/DELETE) : méthodes autorisées par défaut par le CRS du WAF.
    @router.post("/habilitations")
    async def grant(
        body: HabilitationIn,
        actor: str = Depends(current_admin),
        use_case: BackOfficeAdmin = Depends(admin_factory),
    ) -> dict[str, str]:
        await _admin_call(use_case.grant(actor, body.identifier, Role(body.role)))
        return {"status": "granted"}

    @router.post("/habilitations/revoke")
    async def revoke(
        body: AdminIdentifyIn,
        actor: str = Depends(current_admin),
        use_case: BackOfficeAdmin = Depends(admin_factory),
    ) -> dict[str, str]:
        await _admin_call(use_case.revoke(actor, body.identifier))
        return {"status": "revoked"}

    @router.get("/lockouts")
    async def lockouts(
        actor: str = Depends(current_admin), use_case: BackOfficeAdmin = Depends(admin_factory)
    ) -> list[LockoutOut]:
        records = await _admin_call(use_case.lockouts(actor))
        return [
            LockoutOut(identifier=r.identifier, locked_until=r.locked_until)
            for r in records
            if r.locked_until is not None
        ]

    @router.post("/lockouts/unlock")
    async def unlock(
        body: AdminIdentifyIn,
        actor: str = Depends(current_admin),
        use_case: BackOfficeAdmin = Depends(admin_factory),
    ) -> dict[str, str]:
        await _admin_call(use_case.unlock(actor, body.identifier))
        return {"status": "unlocked"}

    @router.get("/journal")
    async def journal(
        actor: str = Depends(current_admin), use_case: BackOfficeAdmin = Depends(admin_factory)
    ) -> list[AccessEntryOut]:
        entries = await _admin_call(use_case.journal(actor))
        return [
            AccessEntryOut(at=e.at, event=e.event, identifier=e.identifier, detail=e.detail)
            for e in entries
        ]

    return router


async def _admin_call(call: Awaitable[T]) -> T:
    """Traduit les erreurs d'administration en codes HTTP (403, 404, 409)."""
    try:
        return await call
    except NotAuthorized as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except UnknownUser as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except CannotRevokeSelf as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


def _locked(exc: AccountLocked) -> HTTPException:
    return HTTPException(
        status.HTTP_423_LOCKED, str(exc), headers={"Retry-After": str(exc.retry_after_seconds)}
    )
