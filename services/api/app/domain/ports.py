"""Ports de l'API métier (DIP) : le domaine et l'application ne connaissent que ceci.

Les ports sont volontairement petits (ISP) : un cas d'usage ne dépend que de ce
dont il a besoin. Les implémentations SQLAlchemy vivent dans `adapters/persistence`
et sont injectées dans `main.py`.
"""

from __future__ import annotations

from collections.abc import Sequence
from types import TracebackType
from typing import Protocol
from uuid import UUID

from app.domain.models import Account, LedgerEntry, Transaction, TransactionView


class AccountRepository(Protocol):
    async def get_by_id(self, account_id: UUID) -> Account | None: ...

    async def get_by_iban(self, iban_fake: str) -> Account | None: ...

    async def get_by_user_id(self, user_id: UUID) -> Account | None: ...

    async def save(self, account: Account) -> None: ...


class TransactionRepository(Protocol):
    async def get_by_id(self, transaction_id: UUID) -> Transaction | None: ...

    async def get_by_idempotency_key(self, key: str) -> Transaction | None: ...

    async def add(self, transaction: Transaction) -> None: ...

    async def add_ledger_entries(self, entries: Sequence[LedgerEntry]) -> None: ...

    async def list_for_account(self, account_id: UUID, limit: int) -> Sequence[TransactionView]: ...


class UnitOfWork(Protocol):
    """Transaction applicative : tout est validé ensemble, ou rien ne l'est.

    Une écriture comptable orpheline casserait l'égalité SUM(debit) = SUM(credit).
    """

    accounts: AccountRepository
    transactions: TransactionRepository

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class TokenVerifier(Protocol):
    """Identifie l'appelant d'un jeton émis par le service d'authentification."""

    def user_id(self, token: str) -> UUID | None:
        """Renvoie l'utilisateur, ou `None` si le jeton est invalide ou expiré."""
        ...


class HealthProbe(Protocol):
    """Vérifie que la base répond (`SELECT 1`) : /health ne doit pas mentir."""

    async def ping(self) -> bool: ...


class EventPublisher(Protocol):
    """Émet un événement JSON structuré (`service`, `trace_id`, `event`) vers Loki."""

    def publish(self, event: str, trace_id: str, **data: object) -> None: ...
