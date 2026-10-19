"""Entités et valeurs du domaine « paiement » (aucune dépendance framework).

Règle absolue : les montants sont des entiers de centimes. Aucun `float` ne touche
à de l'argent, sous peine d'écarts de comptabilité impossibles à prouver au jury.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.errors import (
    CurrencyMismatch,
    InsufficientFunds,
    InvalidAmount,
    SameAccountTransfer,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> UUID:
    return uuid4()


class UserRole(StrEnum):
    """Rôle applicatif ; l'habilitation fine reste au service d'authentification."""

    CUSTOMER = "customer"
    MERCHANT = "merchant"
    PROBE = "probe"  # compte de sonde du moteur de remédiation
    ADMIN = "admin"


class TransactionStatus(StrEnum):
    PENDING = "pending"
    SETTLED = "settled"
    FAILED = "failed"
    REJECTED = "rejected"


class LedgerDirection(StrEnum):
    DEBIT = "debit"
    CREDIT = "credit"


@dataclass(frozen=True)
class User:
    email: str
    password_hash: str  # argon2 ; jamais le mot de passe en clair
    role: UserRole = UserRole.CUSTOMER
    id: UUID = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)


@dataclass(frozen=True)
class Merchant:
    name: str
    mcc: str  # Merchant Category Code (4 chiffres)
    api_key_hash: str  # seul le hachage est stocké
    id: UUID = field(default_factory=_new_id)


@dataclass
class Account:
    """Compte de paiement. Le solde ne peut changer que par débit ou crédit."""

    user_id: UUID
    iban_fake: str  # identifiant fictif de laboratoire, aucune donnée bancaire réelle
    balance_cents: int = 0
    currency: str = "EUR"
    id: UUID = field(default_factory=_new_id)

    def ensure_currency(self, currency: str) -> None:
        if currency != self.currency:
            raise CurrencyMismatch(
                f"compte {self.iban_fake} en {self.currency}, opération en {currency}"
            )

    def debit(self, amount_cents: int, currency: str) -> None:
        _check_amount(amount_cents)
        self.ensure_currency(currency)
        if self.balance_cents < amount_cents:
            raise InsufficientFunds(
                f"solde insuffisant sur {self.iban_fake} : "
                f"{self.balance_cents} < {amount_cents} centimes"
            )
        self.balance_cents -= amount_cents

    def credit(self, amount_cents: int, currency: str) -> None:
        _check_amount(amount_cents)
        self.ensure_currency(currency)
        self.balance_cents += amount_cents


@dataclass(frozen=True)
class LedgerEntry:
    """Écriture comptable. Une transaction réglée en produit exactement deux."""

    transaction_id: UUID
    account_id: UUID
    direction: LedgerDirection
    amount_cents: int
    id: UUID = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)


@dataclass
class Transaction:
    account_from: UUID
    account_to: UUID
    amount_cents: int
    idempotency_key: str
    trace_id: str
    currency: str = "EUR"
    status: TransactionStatus = TransactionStatus.PENDING
    id: UUID = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        _check_amount(self.amount_cents)
        if self.account_from == self.account_to:
            raise SameAccountTransfer("les comptes source et destination sont identiques")

    def settle(self) -> tuple[LedgerEntry, LedgerEntry]:
        """Passe la transaction à `settled` et produit les deux écritures (double entrée)."""
        self.status = TransactionStatus.SETTLED
        return (
            LedgerEntry(
                transaction_id=self.id,
                account_id=self.account_from,
                direction=LedgerDirection.DEBIT,
                amount_cents=self.amount_cents,
            ),
            LedgerEntry(
                transaction_id=self.id,
                account_id=self.account_to,
                direction=LedgerDirection.CREDIT,
                amount_cents=self.amount_cents,
            ),
        )

    def reject(self) -> None:
        """Refus métier (solde, devise) : conservé en base, c'est une trace d'audit."""
        self.status = TransactionStatus.REJECTED

    def fail(self) -> None:
        """Échec technique : distinct d'un refus métier pour le diagnostic d'incident."""
        self.status = TransactionStatus.FAILED


@dataclass(frozen=True)
class TransactionView:
    """Lecture d'historique : la transaction avec les IBAN fictifs de ses deux comptes."""

    transaction: Transaction
    from_iban: str
    to_iban: str


def _check_amount(amount_cents: int) -> None:
    if not isinstance(amount_cents, int) or isinstance(amount_cents, bool):
        raise InvalidAmount("le montant doit être un entier de centimes")
    if amount_cents <= 0:
        raise InvalidAmount("le montant doit être strictement positif")
