"""Schémas Pydantic : conversion HTTP <-> domaine, aucune règle métier ici."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.models import Account, Transaction, TransactionStatus, TransactionView


class TransferIn(BaseModel):
    """Entrée d'un virement : le montant est un entier de centimes, jamais un `float`."""

    from_account: str = Field(min_length=1, max_length=34)  # IBAN fictif source
    to_account: str = Field(min_length=1, max_length=34)  # IBAN fictif destinataire
    amount_cents: int = Field(gt=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    idempotency_key: str | None = Field(default=None, max_length=64)

    @field_validator("currency")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()


class TransactionOut(BaseModel):
    id: UUID
    account_from: UUID
    account_to: UUID
    amount_cents: int
    currency: str
    status: TransactionStatus
    idempotency_key: str
    trace_id: str
    created_at: datetime

    @classmethod
    def from_domain(cls, transaction: Transaction) -> TransactionOut:
        return cls(
            id=transaction.id,
            account_from=transaction.account_from,
            account_to=transaction.account_to,
            amount_cents=transaction.amount_cents,
            currency=transaction.currency,
            status=transaction.status,
            idempotency_key=transaction.idempotency_key,
            trace_id=transaction.trace_id,
            created_at=transaction.created_at,
        )


class AccountOut(BaseModel):
    id: UUID
    iban_fake: str
    balance_cents: int
    currency: str

    @classmethod
    def from_domain(cls, account: Account) -> AccountOut:
        return cls(
            id=account.id,
            iban_fake=account.iban_fake,
            balance_cents=account.balance_cents,
            currency=account.currency,
        )


class HealthOut(BaseModel):
    status: str
    database: str


class MyTransferIn(BaseModel):
    """Virement d'un client : la source est celle de son jeton, jamais celle du corps."""

    to_account: str = Field(min_length=1, max_length=34)
    amount_cents: int = Field(gt=0)
    idempotency_key: str = Field(min_length=8, max_length=64)  # générée par le front par envoi


class HistoryItemOut(BaseModel):
    id: UUID
    direction: str  # "debit" si le client a payé, "credit" s'il a reçu
    counterparty_iban: str
    amount_cents: int
    currency: str
    status: TransactionStatus
    created_at: datetime

    @classmethod
    def from_view(cls, view: TransactionView, own_account_id: UUID) -> HistoryItemOut:
        paid = view.transaction.account_from == own_account_id
        return cls(
            id=view.transaction.id,
            direction="debit" if paid else "credit",
            counterparty_iban=view.to_iban if paid else view.from_iban,
            amount_cents=view.transaction.amount_cents,
            currency=view.transaction.currency,
            status=view.transaction.status,
            created_at=view.transaction.created_at,
        )
