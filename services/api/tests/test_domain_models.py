"""Tests du domaine : aucune I/O, aucun framework."""

from __future__ import annotations

import pytest

from app.domain.errors import (
    CurrencyMismatch,
    InsufficientFunds,
    InvalidAmount,
    SameAccountTransfer,
)
from app.domain.models import (
    LedgerDirection,
    Transaction,
    TransactionStatus,
    UserRole,
)
from tests.fakes import make_account, make_user


def test_le_role_de_la_sonde_existe() -> None:
    assert make_user().role is UserRole.PROBE


def test_debit_puis_credit_conservent_la_masse_monetaire() -> None:
    source = make_account("TEST-0001", 10_000)
    destination = make_account("TEST-0002", 0)

    source.debit(2_500, "EUR")
    destination.credit(2_500, "EUR")

    assert source.balance_cents == 7_500
    assert destination.balance_cents == 2_500


def test_debit_refuse_un_solde_insuffisant() -> None:
    account = make_account("TEST-0001", 100)
    with pytest.raises(InsufficientFunds):
        account.debit(101, "EUR")
    assert account.balance_cents == 100  # aucun effet de bord


def test_debit_refuse_une_devise_differente() -> None:
    account = make_account("TEST-0001", 10_000)
    with pytest.raises(CurrencyMismatch):
        account.debit(100, "USD")


@pytest.mark.parametrize("amount", [0, -1])
def test_montant_non_positif_refuse(amount: int) -> None:
    account = make_account("TEST-0001", 10_000)
    with pytest.raises(InvalidAmount):
        account.credit(amount, "EUR")


def test_montant_flottant_refuse() -> None:
    """Jamais de float sur de l'argent : 0.1 + 0.2 != 0.3."""
    account = make_account("TEST-0001", 10_000)
    with pytest.raises(InvalidAmount):
        account.credit(1.5, "EUR")  # type: ignore[arg-type]


def _transaction(amount_cents: int = 1_000) -> Transaction:
    source = make_account("TEST-0001", 10_000)
    destination = make_account("TEST-0002", 0)
    return Transaction(
        account_from=source.id,
        account_to=destination.id,
        amount_cents=amount_cents,
        idempotency_key="cle-1",
        trace_id="trace-1",
    )


def test_virement_vers_le_meme_compte_refuse() -> None:
    account = make_account("TEST-0001", 10_000)
    with pytest.raises(SameAccountTransfer):
        Transaction(
            account_from=account.id,
            account_to=account.id,
            amount_cents=100,
            idempotency_key="cle-1",
            trace_id="trace-1",
        )


def test_reglement_produit_deux_ecritures_equilibrees() -> None:
    transaction = _transaction(4_200)

    debit, credit = transaction.settle()

    assert transaction.status is TransactionStatus.SETTLED
    assert debit.direction is LedgerDirection.DEBIT
    assert credit.direction is LedgerDirection.CREDIT
    assert debit.account_id == transaction.account_from
    assert credit.account_id == transaction.account_to
    # Double entrée : SUM(debit) = SUM(credit).
    assert debit.amount_cents == credit.amount_cents == 4_200
    assert debit.transaction_id == credit.transaction_id == transaction.id


def test_refus_et_echec_sont_des_etats_distincts() -> None:
    rejected = _transaction()
    rejected.reject()
    failed = _transaction()
    failed.fail()

    assert rejected.status is TransactionStatus.REJECTED
    assert failed.status is TransactionStatus.FAILED
