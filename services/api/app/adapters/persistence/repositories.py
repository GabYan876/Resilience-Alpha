"""Implémentations SQLAlchemy des ports de dépôt (adaptateurs interchangeables, LSP)."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.adapters.persistence.models import AccountRow, LedgerEntryRow, TransactionRow
from app.domain.models import Account, LedgerEntry, Transaction, TransactionView


def _to_account(row: AccountRow) -> Account:
    return Account(
        id=row.id,
        user_id=row.user_id,
        iban_fake=row.iban_fake,
        balance_cents=row.balance_cents,
        currency=row.currency,
    )


def _to_transaction(row: TransactionRow) -> Transaction:
    return Transaction(
        id=row.id,
        account_from=row.account_from,
        account_to=row.account_to,
        amount_cents=row.amount_cents,
        currency=row.currency,
        status=row.status,
        idempotency_key=row.idempotency_key,
        trace_id=row.trace_id,
        created_at=row.created_at,
    )


class SqlAlchemyAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._rows: dict[UUID, AccountRow] = {}

    async def get_by_id(self, account_id: UUID) -> Account | None:
        row = await self._session.get(AccountRow, account_id)
        return self._track(row)

    async def get_by_iban(self, iban_fake: str) -> Account | None:
        # `FOR UPDATE` : sous flood, deux virements simultanés ne doivent pas se
        # baser sur le même solde (mise à jour perdue = comptabilité fausse).
        statement = select(AccountRow).where(AccountRow.iban_fake == iban_fake).with_for_update()
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return self._track(row)

    async def get_by_user_id(self, user_id: UUID) -> Account | None:
        # Lecture seule (pas de verrou). Un client a un compte ; au besoin le premier IBAN.
        statement = (
            select(AccountRow)
            .where(AccountRow.user_id == user_id)
            .order_by(AccountRow.iban_fake)
            .limit(1)
        )
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return _to_account(row) if row is not None else None

    async def save(self, account: Account) -> None:
        row = self._rows.get(account.id) or await self._session.get(AccountRow, account.id)
        if row is None:
            raise LookupError(f"compte absent en base : {account.id}")
        row.balance_cents = account.balance_cents
        row.currency = account.currency

    def _track(self, row: AccountRow | None) -> Account | None:
        if row is None:
            return None
        self._rows[row.id] = row
        return _to_account(row)


class SqlAlchemyTransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, transaction_id: UUID) -> Transaction | None:
        row = await self._session.get(TransactionRow, transaction_id)
        return _to_transaction(row) if row is not None else None

    async def get_by_idempotency_key(self, key: str) -> Transaction | None:
        statement = select(TransactionRow).where(TransactionRow.idempotency_key == key)
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return _to_transaction(row) if row is not None else None

    async def add(self, transaction: Transaction) -> None:
        self._session.add(
            TransactionRow(
                id=transaction.id,
                account_from=transaction.account_from,
                account_to=transaction.account_to,
                amount_cents=transaction.amount_cents,
                currency=transaction.currency,
                status=transaction.status,
                idempotency_key=transaction.idempotency_key,
                trace_id=transaction.trace_id,
            )
        )
        # Les écritures du grand livre référencent cette ligne par clé étrangère.
        # Aucune `relationship()` ne lie les deux mappers (les lignes restent
        # passives), donc SQLAlchemy ignore la dépendance et ordonne les INSERT
        # par mapper : `ledger_entries` passerait avant `transactions`. Le flush
        # garantit que la transaction parente existe avant les écritures.
        await self._session.flush()

    async def add_ledger_entries(self, entries: Sequence[LedgerEntry]) -> None:
        self._session.add_all(
            [
                LedgerEntryRow(
                    id=entry.id,
                    transaction_id=entry.transaction_id,
                    account_id=entry.account_id,
                    direction=entry.direction,
                    amount_cents=entry.amount_cents,
                )
                for entry in entries
            ]
        )

    async def list_for_account(self, account_id: UUID, limit: int) -> Sequence[TransactionView]:
        source, target = aliased(AccountRow), aliased(AccountRow)
        statement = (
            select(TransactionRow, source.iban_fake, target.iban_fake)
            .join(source, TransactionRow.account_from == source.id)
            .join(target, TransactionRow.account_to == target.id)
            .where(
                or_(
                    TransactionRow.account_from == account_id,
                    TransactionRow.account_to == account_id,
                )
            )
            .order_by(TransactionRow.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        return [TransactionView(_to_transaction(t), src, dst) for t, src, dst in rows]
