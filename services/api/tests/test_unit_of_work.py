"""Tests des adaptateurs de persistance avec une session factice (aucune base)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from app.adapters.persistence.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyTransactionRepository,
)
from app.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.models import LedgerDirection, LedgerEntry, Transaction, TransactionStatus
from tests.fakes import make_account

pytestmark = pytest.mark.anyio


class FakeSession:
    """Double de `AsyncSession` : enregistre les appels, ne parle à aucune base."""

    def __init__(self, rows: dict[Any, Any] | None = None) -> None:
        self.rows = rows or {}
        self.added: list[Any] = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0
        # Nombre de lignes déjà ajoutées à chaque flush : permet de prouver
        # qu'une ligne parente est écrite avant les lignes qui la référencent.
        self.flushed_after: list[int] = []

    async def get(self, _model: Any, key: Any) -> Any:
        return self.rows.get(key)

    def add(self, row: Any) -> None:
        self.added.append(row)

    def add_all(self, rows: Any) -> None:
        self.added.extend(rows)

    async def flush(self) -> None:
        self.flushed_after.append(len(self.added))

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def close(self) -> None:
        self.closed += 1


async def test_l_unite_de_travail_annule_et_ferme_en_sortie_de_bloc() -> None:
    session = FakeSession()
    uow = SqlAlchemyUnitOfWork(lambda: session)  # type: ignore[arg-type]

    async with uow:
        pass

    assert session.rollbacks == 1  # sans commit explicite, rien n'est validé
    assert session.closed == 1


async def test_l_unite_de_travail_valide_puis_ferme() -> None:
    session = FakeSession()
    uow = SqlAlchemyUnitOfWork(lambda: session)  # type: ignore[arg-type]

    async with uow as opened:
        await opened.commit()

    assert session.commits == 1
    assert session.closed == 1


async def test_l_unite_de_travail_refuse_d_etre_utilisee_hors_de_son_bloc() -> None:
    uow = SqlAlchemyUnitOfWork(lambda: FakeSession())  # type: ignore[arg-type]

    with pytest.raises(RuntimeError):
        await uow.commit()


async def test_un_depot_de_comptes_sans_ligne_en_base_echoue_clairement() -> None:
    repository = SqlAlchemyAccountRepository(FakeSession())  # type: ignore[arg-type]

    with pytest.raises(LookupError):
        await repository.save(make_account("TEST-0001", 100))


async def test_la_transaction_est_ecrite_avec_tous_ses_champs() -> None:
    session = FakeSession()
    repository = SqlAlchemyTransactionRepository(session)  # type: ignore[arg-type]
    transaction = Transaction(
        account_from=uuid4(),
        account_to=uuid4(),
        amount_cents=4_200,
        currency="EUR",
        idempotency_key="cle-1",
        trace_id="trace-1",
        status=TransactionStatus.SETTLED,
    )

    await repository.add(transaction)

    row = session.added[0]
    assert row.id == transaction.id
    assert row.amount_cents == 4_200
    assert row.status is TransactionStatus.SETTLED
    assert row.idempotency_key == "cle-1"
    assert row.trace_id == "trace-1"


async def test_la_transaction_est_flushee_avant_les_ecritures_du_grand_livre() -> None:
    """Régression : `ledger_entries` référence `transactions` par clé étrangère.

    Aucune `relationship()` ne lie les deux mappers, donc SQLAlchemy ordonne les
    INSERT par mapper et insérerait les écritures avant la transaction parente.
    Sans ce flush, PostgreSQL rejette l'insertion en ForeignKeyViolationError.
    """
    session = FakeSession()
    repository = SqlAlchemyTransactionRepository(session)  # type: ignore[arg-type]
    transaction = Transaction(
        account_from=uuid4(),
        account_to=uuid4(),
        amount_cents=100,
        currency="EUR",
        idempotency_key="cle-flush",
        trace_id="trace-flush",
        status=TransactionStatus.SETTLED,
    )

    await repository.add(transaction)
    await repository.add_ledger_entries(
        [
            LedgerEntry(
                transaction_id=transaction.id,
                account_id=uuid4(),
                direction=LedgerDirection.DEBIT,
                amount_cents=100,
            )
        ]
    )

    # Un seul flush, déclenché alors que seule la transaction était ajoutée.
    assert session.flushed_after == [1]


async def test_les_ecritures_du_grand_livre_sont_ajoutees_en_bloc() -> None:
    session = FakeSession()
    repository = SqlAlchemyTransactionRepository(session)  # type: ignore[arg-type]
    transaction_id = uuid4()
    entries = [
        LedgerEntry(
            transaction_id=transaction_id,
            account_id=uuid4(),
            direction=LedgerDirection.DEBIT,
            amount_cents=100,
        ),
        LedgerEntry(
            transaction_id=transaction_id,
            account_id=uuid4(),
            direction=LedgerDirection.CREDIT,
            amount_cents=100,
        ),
    ]

    await repository.add_ledger_entries(entries)

    assert [row.direction for row in session.added] == [
        LedgerDirection.DEBIT,
        LedgerDirection.CREDIT,
    ]
    assert {row.transaction_id for row in session.added} == {transaction_id}
