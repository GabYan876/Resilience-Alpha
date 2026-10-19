"""Routes du client authentifié (`/me/*`) : solde, historique, virement.

L'identité vient uniquement du jeton (`sub`). Le compte source d'un virement n'est jamais lu
dans le corps de la requête : un client ne peut donc pas débiter le compte d'un autre.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status

from app.api.schemas import AccountOut, HistoryItemOut, MyTransferIn, TransactionOut
from app.api.transfer_http import run_transfer
from app.application.queries import GetUserAccount, ListUserTransactions
from app.application.transfer import ExecuteTransfer, TransferCommand
from app.domain.errors import AccountNotFound
from app.domain.ports import TokenVerifier, UnitOfWork


def build_me_router(
    uow_factory: Callable[[], UnitOfWork],
    transfer_factory: Callable[[], ExecuteTransfer],
    verifier: TokenVerifier,
) -> APIRouter:
    router = APIRouter(prefix="/me")

    def current_user(authorization: str = Header(default="")) -> UUID:
        user_id = verifier.user_id(authorization.removeprefix("Bearer "))
        if user_id is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "jeton invalide ou expiré")
        return user_id

    @router.get("/account", response_model=AccountOut)
    async def my_account(user_id: UUID = Depends(current_user)) -> AccountOut:
        try:
            account = await GetUserAccount(uow_factory()).execute(user_id)
        except AccountNotFound as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        return AccountOut.from_domain(account)

    @router.get("/transactions", response_model=list[HistoryItemOut])
    async def my_transactions(
        limit: int = Query(default=20, ge=1, le=100), user_id: UUID = Depends(current_user)
    ) -> list[HistoryItemOut]:
        try:
            account, views = await ListUserTransactions(uow_factory()).execute(user_id, limit)
        except AccountNotFound as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        return [HistoryItemOut.from_view(view, account.id) for view in views]

    @router.post("/transfers", response_model=TransactionOut)
    async def my_transfer(
        body: MyTransferIn,
        response: Response,
        user_id: UUID = Depends(current_user),
        transfer: ExecuteTransfer = Depends(transfer_factory),
    ) -> TransactionOut:
        try:
            own = await GetUserAccount(uow_factory()).execute(user_id)
        except AccountNotFound as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        # La clé est liée à l'utilisateur : sans cela, rejouer la clé d'autrui renverrait
        # sa transaction (le contrôle d'idempotence est global à la base).
        scoped_key = hashlib.sha256(f"{user_id}:{body.idempotency_key}".encode()).hexdigest()
        return await run_transfer(
            transfer,
            lambda: TransferCommand(
                from_iban=own.iban_fake,
                to_iban=body.to_account,
                amount_cents=body.amount_cents,
                idempotency_key=scoped_key,
            ),
            response,
        )

    return router
