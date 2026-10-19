"""Doubles de test : implémentations en mémoire des ports (LSP).

Le domaine et l'application sont testés sans PostgreSQL ni HTTP.
"""

from __future__ import annotations

from collections.abc import Sequence
from types import TracebackType
from uuid import UUID, uuid4

from app.domain.models import Account, LedgerEntry, Transaction, User, UserRole


class InMemoryAccountRepository:
    def __init__(self, accounts: Sequence[Account] = ()) -> None:
        self.by_id: dict[UUID, Account] = {a.id: a for a in accounts}
        self.saved: list[UUID] = []

    async def get_by_id(self, account_id: UUID) -> Account | None:
        return self.by_id.get(account_id)

    async def get_by_iban(self, iban_fake: str) -> Account | None:
        return next((a for a in self.by_id.values() if a.iban_fake == iban_fake), None)

    async def save(self, account: Account) -> None:
        self.by_id[account.id] = account
        self.saved.append(account.id)


class InMemoryTransactionRepository:
    def __init__(self) -> None:
        self.transactions: dict[UUID, Transaction] = {}
        self.ledger: list[LedgerEntry] = []

    async def get_by_id(self, transaction_id: UUID) -> Transaction | None:
        return self.transactions.get(transaction_id)

    async def get_by_idempotency_key(self, key: str) -> Transaction | None:
        return next(
            (t for t in self.transactions.values() if t.idempotency_key == key),
            None,
        )

    async def add(self, transaction: Transaction) -> None:
        self.transactions[transaction.id] = transaction

    async def add_ledger_entries(self, entries: Sequence[LedgerEntry]) -> None:
        self.ledger.extend(entries)


class FakeUnitOfWork:
    """Unité de travail en mémoire. Compte les commits et les rollbacks."""

    def __init__(
        self,
        accounts: InMemoryAccountRepository | None = None,
        transactions: InMemoryTransactionRepository | None = None,
    ) -> None:
        self.accounts = accounts or InMemoryAccountRepository()
        self.transactions = transactions or InMemoryTransactionRepository()
        self.commits = 0
        self.rollbacks = 0
        self.entered = 0

    async def __aenter__(self) -> FakeUnitOfWork:
        self.entered += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class RecordingPublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, object]]] = []

    def publish(self, event: str, trace_id: str, **data: object) -> None:
        self.events.append((event, trace_id, data))

    @property
    def names(self) -> list[str]:
        return [event for event, _, _ in self.events]


class AlwaysHealthyProbe:
    async def ping(self) -> bool:
        return True


class AlwaysDownProbe:
    async def ping(self) -> bool:
        return False


def make_user(email: str = "probe@resilience.local") -> User:
    return User(email=email, password_hash="$argon2id$fake", role=UserRole.PROBE)


def make_account(iban: str, balance_cents: int, currency: str = "EUR") -> Account:
    return Account(
        id=uuid4(),
        user_id=uuid4(),
        iban_fake=iban,
        balance_cents=balance_cents,
        currency=currency,
    )
