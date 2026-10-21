"""Routes FastAPI : traduction HTTP <-> cas d'usage, aucune logique métier.

Les fabriques (`Callable[[], ...]`) sont injectées par `main.py` : les routes
ignorent SQLAlchemy et PostgreSQL.
"""

from __future__ import annotations

import hmac
from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.api.schemas import AccountOut, HealthOut, TransactionOut, TransferIn
from app.api.transfer_http import run_transfer
from app.application.queries import GetAccount, GetTransaction
from app.application.transfer import ExecuteTransfer, TransferCommand
from app.domain.errors import AccountNotFound
from app.domain.ports import HealthProbe, UnitOfWork


def build_router(
    uow_factory: Callable[[], UnitOfWork],
    transfer_factory: Callable[[], ExecuteTransfer],
    health_probe: HealthProbe,
    get_write_token: Callable[[], str],
) -> APIRouter:
    router = APIRouter()

    def require_token(authorization: str = Header(default="")) -> None:
        """Protège les écritures. Jeton vide = garde désactivée (dev local uniquement)."""
        expected = get_write_token()
        if not expected:
            return
        supplied = authorization.removeprefix("Bearer ")
        if not hmac.compare_digest(supplied, expected):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "jeton invalide")

    @router.get("/health", response_model=HealthOut)
    async def health(response: Response) -> HealthOut:
        database_up = await health_probe.ping()
        if not database_up:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return HealthOut(status="degraded", database="down")
        return HealthOut(status="ok", database="up")

    @router.post(
        "/transactions",
        response_model=TransactionOut,
        dependencies=[Depends(require_token)],
    )
    async def create_transaction(
        body: TransferIn,
        response: Response,
        transfer: ExecuteTransfer = Depends(transfer_factory),
    ) -> TransactionOut:
        return await run_transfer(
            transfer,
            lambda: TransferCommand(
                from_iban=body.from_account,
                to_iban=body.to_account,
                amount_cents=body.amount_cents,
                currency=body.currency,
                idempotency_key=body.idempotency_key,
            ),
            response,
        )

    @router.get("/transactions/{transaction_id}", response_model=TransactionOut)
    async def read_transaction(transaction_id: UUID) -> TransactionOut:
        transaction = await GetTransaction(uow_factory()).execute(transaction_id)
        if transaction is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "transaction inconnue")
        return TransactionOut.from_domain(transaction)

    @router.get("/accounts/{iban_fake}", response_model=AccountOut)
    async def read_account(iban_fake: str) -> AccountOut:
        try:
            account = await GetAccount(uow_factory()).execute(iban_fake)
        except AccountNotFound as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        return AccountOut.from_domain(account)

    return router
