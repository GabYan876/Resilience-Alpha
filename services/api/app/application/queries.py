"""Cas d'usage de lecture : consultation d'une transaction ou d'un compte."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.domain.errors import AccountNotFound
from app.domain.models import Account, Transaction, TransactionView
from app.domain.ports import UnitOfWork


class GetTransaction:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, transaction_id: UUID) -> Transaction | None:
        async with self._uow as uow:
            return await uow.transactions.get_by_id(transaction_id)


class GetAccount:
    """Sert aussi au script de vérification : le solde de la sonde doit rester suffisant."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, iban_fake: str) -> Account:
        async with self._uow as uow:
            account = await uow.accounts.get_by_iban(iban_fake)
        if account is None:
            raise AccountNotFound(f"compte inconnu : {iban_fake}")
        return account


class GetUserAccount:
    """Compte du client authentifié (solde affiché par le front)."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID) -> Account:
        async with self._uow as uow:
            account = await uow.accounts.get_by_user_id(user_id)
        if account is None:
            raise AccountNotFound("aucun compte pour cet utilisateur")
        return account


class ListUserTransactions:
    """Historique du client, du plus récent au plus ancien."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID, limit: int) -> tuple[Account, Sequence[TransactionView]]:
        async with self._uow as uow:
            account = await uow.accounts.get_by_user_id(user_id)
            if account is None:
                raise AccountNotFound("aucun compte pour cet utilisateur")
            return account, await uow.transactions.list_for_account(account.id, limit)
