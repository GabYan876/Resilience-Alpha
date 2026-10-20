"""Tests du cas d'usage de virement, avec des doubles en mémoire."""

from __future__ import annotations

import pytest

from app.application.transfer import ExecuteTransfer, TransferCommand
from app.domain.errors import AccountNotFound
from app.domain.models import LedgerDirection, TransactionStatus
from tests.fakes import (
    FakeUnitOfWork,
    InMemoryAccountRepository,
    RecordingPublisher,
    make_account,
)

pytestmark = pytest.mark.anyio


def _setup(
    balance_cents: int = 10_000,
) -> tuple[ExecuteTransfer, FakeUnitOfWork, RecordingPublisher]:
    source = make_account("TEST-0001", balance_cents)
    destination = make_account("TEST-0002", 0)
    uow = FakeUnitOfWork(InMemoryAccountRepository([source, destination]))
    publisher = RecordingPublisher()
    return ExecuteTransfer(uow, publisher), uow, publisher


def _command(**changes: object) -> TransferCommand:
    base: dict[str, object] = {
        "from_iban": "TEST-0001",
        "to_iban": "TEST-0002",
        "amount_cents": 1_000,
    }
    base.update(changes)
    return TransferCommand(**base)  # type: ignore[arg-type]


async def test_virement_regle_met_a_jour_les_soldes_et_le_grand_livre() -> None:
    transfer, uow, publisher = _setup()

    transaction = await transfer.execute(_command(idempotency_key="cle-1"))

    assert transaction.status is TransactionStatus.SETTLED
    source = await uow.accounts.get_by_iban("TEST-0001")
    destination = await uow.accounts.get_by_iban("TEST-0002")
    assert source is not None and destination is not None
    assert source.balance_cents == 9_000
    assert destination.balance_cents == 1_000
    assert uow.commits == 1
    assert "transaction.settled" in publisher.names


async def test_grand_livre_equilibre() -> None:
    transfer, uow, _ = _setup()

    await transfer.execute(_command(amount_cents=2_500))

    debits = [e for e in uow.transactions.ledger if e.direction is LedgerDirection.DEBIT]
    credits = [e for e in uow.transactions.ledger if e.direction is LedgerDirection.CREDIT]
    assert len(debits) == len(credits) == 1
    assert sum(e.amount_cents for e in debits) == sum(e.amount_cents for e in credits)


async def test_meme_cle_d_idempotence_ne_debite_qu_une_fois() -> None:
    """La sonde de reprise peut être rejouée : pas de double débit."""
    transfer, uow, publisher = _setup()

    first = await transfer.execute(_command(idempotency_key="cle-sonde"))
    second = await transfer.execute(_command(idempotency_key="cle-sonde"))

    assert first.id == second.id
    source = await uow.accounts.get_by_iban("TEST-0001")
    assert source is not None
    assert source.balance_cents == 9_000
    assert publisher.names.count("transaction.replayed") == 1
    assert len(uow.transactions.ledger) == 2  # une seule transaction réglée


async def test_solde_insuffisant_rejette_sans_toucher_aux_soldes() -> None:
    transfer, uow, publisher = _setup(balance_cents=500)

    transaction = await transfer.execute(_command(amount_cents=1_000))

    assert transaction.status is TransactionStatus.REJECTED
    source = await uow.accounts.get_by_iban("TEST-0001")
    assert source is not None
    assert source.balance_cents == 500
    assert uow.transactions.ledger == []  # aucune écriture comptable
    assert "transaction.rejected" in publisher.names
    # Le refus est conservé en base : c'est une trace d'audit, pas une panne.
    assert await uow.transactions.get_by_id(transaction.id) is transaction


async def test_devise_incoherente_rejette() -> None:
    transfer, _, _ = _setup()

    transaction = await transfer.execute(_command(currency="USD"))

    assert transaction.status is TransactionStatus.REJECTED


async def test_compte_inconnu_leve_une_erreur_de_domaine() -> None:
    transfer, _, publisher = _setup()

    with pytest.raises(AccountNotFound):
        await transfer.execute(_command(from_iban="INCONNU"))

    assert "transaction.unknown_account" in publisher.names


async def test_chaque_evenement_porte_le_meme_trace_id() -> None:
    transfer, _, publisher = _setup()

    transaction = await transfer.execute(_command(trace_id="trace-demo"))

    assert transaction.trace_id == "trace-demo"
    assert {trace_id for _, trace_id, _ in publisher.events} == {"trace-demo"}


async def test_les_verrous_sont_pris_dans_l_ordre_des_iban_quel_que_soit_le_sens() -> None:
    # Régression : A -> B et B -> A prenaient les verrous en sens inverse (deadlock PostgreSQL).
    for from_iban, to_iban in (("TEST-0001", "TEST-0002"), ("TEST-0002", "TEST-0001")):
        transfer, uow, _ = _setup()

        await transfer.execute(_command(from_iban=from_iban, to_iban=to_iban))

        assert uow.accounts.lookups == ["TEST-0001", "TEST-0002"]
