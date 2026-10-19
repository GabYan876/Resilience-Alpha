"""Schémas Pydantic : conversion HTTP <-> domaine, aucune règle métier ici."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.models import Account, Transaction, TransactionStatus, TransactionView

_CENTS = Decimal(100)


class TransferIn(BaseModel):
    """Entrée d'un virement.

    Deux formes de montant sont acceptées :
    - `amount_cents` (entier, forme canonique) ;
    - `amount` (unités, ex. 1.50) converti en centimes via `Decimal`.

    La seconde existe pour la sonde du moteur de remédiation
    (`services/remediation/app/adapters/api_probe.py`), qui envoie `amount`.
    """

    from_account: str = Field(min_length=1, max_length=34)  # IBAN fictif source
    to_account: str = Field(min_length=1, max_length=34)  # IBAN fictif destinataire
    amount_cents: int | None = Field(default=None, gt=0)
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    idempotency_key: str | None = Field(default=None, max_length=64)

    @field_validator("currency")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def _exactly_one_amount(self) -> TransferIn:
        if (self.amount_cents is None) == (self.amount is None):
            raise ValueError("fournir soit `amount_cents`, soit `amount`, mais pas les deux")
        return self

    def to_cents(self) -> int:
        """Convertit sans jamais passer par un `float`."""
        if self.amount_cents is not None:
            return self.amount_cents
        if self.amount is None:  # garanti par `_exactly_one_amount`
            raise ValueError("montant manquant")
        try:
            cents = (self.amount * _CENTS).normalize()
        except InvalidOperation as exc:  # montant hors limites décimales
            raise ValueError("montant invalide") from exc
        if cents != cents.to_integral_value():
            raise ValueError("montant plus précis que le centime")
        return int(cents)


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
