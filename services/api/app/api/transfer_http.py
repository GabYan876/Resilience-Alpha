"""Traduction d'un virement en réponse HTTP, partagée par la sonde et les clients."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, Response, status

from app.api.schemas import TransactionOut
from app.application.transfer import ExecuteTransfer, TransferCommand
from app.domain.errors import AccountNotFound, DomainError
from app.domain.models import TransactionStatus


async def run_transfer(
    transfer: ExecuteTransfer, build_command: Callable[[], TransferCommand], response: Response
) -> TransactionOut:
    try:
        transaction = await transfer.execute(build_command())
    except AccountNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except (DomainError, ValueError) as exc:  # ValueError : conversion de montant
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    if transaction.status is not TransactionStatus.SETTLED:
        # Refus métier : 409, pour que la sonde de reprise ne le lise pas comme un succès.
        response.status_code = status.HTTP_409_CONFLICT
    return TransactionOut.from_domain(transaction)
