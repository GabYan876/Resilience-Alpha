"""Cas d'usage : exécuter un virement entre deux comptes.

C'est le chemin critique de la démonstration : la sonde du moteur de remédiation
appelle ce cas d'usage pour prouver la reprise après incident.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.domain.errors import AccountNotFound, CurrencyMismatch, InsufficientFunds
from app.domain.models import Transaction, TransactionStatus
from app.domain.ports import EventPublisher, UnitOfWork


@dataclass(frozen=True)
class TransferCommand:
    """Entrée du cas d'usage. Les comptes sont désignés par leur IBAN fictif."""

    from_iban: str
    to_iban: str
    amount_cents: int
    currency: str = "EUR"
    idempotency_key: str | None = None
    trace_id: str | None = None


class ExecuteTransfer:
    """Débite, crédite et écrit les deux lignes de grand livre, en une transaction."""

    def __init__(self, uow: UnitOfWork, publisher: EventPublisher) -> None:
        self._uow = uow
        self._publisher = publisher

    async def execute(self, command: TransferCommand) -> Transaction:
        trace_id = command.trace_id or uuid4().hex
        idempotency_key = command.idempotency_key or uuid4().hex

        async with self._uow as uow:
            existing = await uow.transactions.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                # Rejouer la même clé ne doit jamais débiter deux fois.
                self._publisher.publish(
                    "transaction.replayed",
                    trace_id,
                    transaction_id=str(existing.id),
                    status=existing.status.value,
                )
                return existing

            # Verrous pris dans l'ordre des IBAN, jamais dans l'ordre source puis destinataire :
            # deux virements croisés (A -> B et B -> A) les prendraient en sens inverse et se
            # bloqueraient mutuellement (deadlock PostgreSQL, 500 côté client).
            locked = {}
            for iban in sorted((command.from_iban, command.to_iban)):
                locked[iban] = await uow.accounts.get_by_iban(iban)
            source = locked[command.from_iban]
            destination = locked[command.to_iban]
            if source is None or destination is None:
                missing = command.from_iban if source is None else command.to_iban
                self._publisher.publish("transaction.unknown_account", trace_id, account=missing)
                raise AccountNotFound(f"compte inconnu : {missing}")

            transaction = Transaction(
                account_from=source.id,
                account_to=destination.id,
                amount_cents=command.amount_cents,
                currency=command.currency,
                idempotency_key=idempotency_key,
                trace_id=trace_id,
            )
            self._publisher.publish(
                "transaction.received",
                trace_id,
                transaction_id=str(transaction.id),
                amount_cents=transaction.amount_cents,
                currency=transaction.currency,
            )

            try:
                source.debit(transaction.amount_cents, transaction.currency)
                destination.credit(transaction.amount_cents, transaction.currency)
            except (InsufficientFunds, CurrencyMismatch) as exc:
                # Refus métier : on garde la trace en base, on ne touche pas aux soldes.
                transaction.reject()
                await uow.transactions.add(transaction)
                await uow.commit()
                self._publisher.publish(
                    "transaction.rejected",
                    trace_id,
                    transaction_id=str(transaction.id),
                    reason=str(exc),
                )
                return transaction

            entries = transaction.settle()
            await uow.transactions.add(transaction)
            await uow.transactions.add_ledger_entries(entries)
            await uow.accounts.save(source)
            await uow.accounts.save(destination)
            await uow.commit()

        self._publisher.publish(
            "transaction.settled",
            trace_id,
            transaction_id=str(transaction.id),
            amount_cents=transaction.amount_cents,
            status=TransactionStatus.SETTLED.value,
        )
        return transaction
