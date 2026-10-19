"""Modèles SQLAlchemy (adaptateur). Le domaine ignore totalement ce module.

`METADATA` est la source de vérité du schéma : Alembic s'y branche
(`services/db/migrations/env.py`) pour détecter les écarts.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    MetaData,
    String,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.models import LedgerDirection, TransactionStatus, UserRole

# Convention de nommage explicite : sans elle, Alembic génère des noms de contraintes
# différents selon les machines et les migrations ne sont plus rejouables à l'identique.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


METADATA = Base.metadata

_UUID_PK: dict[str, object] = {"primary_key": True, "default": uuid4}


def _enum(enum_type: type, name: str) -> Enum:
    """Enum PostgreSQL stockant les *valeurs* (minuscules), pas les noms Python."""
    return Enum(
        enum_type,
        name=name,
        values_callable=lambda e: [member.value for member in e],
        native_enum=True,
    )


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(**_UUID_PK)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # argon2
    role: Mapped[UserRole] = mapped_column(
        _enum(UserRole, "user_role"), nullable=False, default=UserRole.CUSTOMER
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MerchantRow(Base):
    __tablename__ = "merchants"

    id: Mapped[UUID] = mapped_column(**_UUID_PK)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    mcc: Mapped[str] = mapped_column(String(4), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (CheckConstraint("mcc ~ '^[0-9]{4}$'", name="mcc_format"),)


class AccountRow(Base):
    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(**_UUID_PK)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    iban_fake: Mapped[str] = mapped_column(String(34), unique=True, nullable=False)
    balance_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")

    __table_args__ = (
        CheckConstraint("balance_cents >= 0", name="balance_non_negative"),
        Index("ix_accounts_user_id", "user_id"),
    )


class TransactionRow(Base):
    __tablename__ = "transactions"

    id: Mapped[UUID] = mapped_column(**_UUID_PK)
    account_from: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    account_to: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    status: Mapped[TransactionStatus] = mapped_column(
        _enum(TransactionStatus, "transaction_status"), nullable=False
    )
    # Clé d'idempotence : la sonde de reprise peut être rejouée sans double débit.
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="amount_positive"),
        CheckConstraint("account_from <> account_to", name="distinct_accounts"),
        Index("ix_transactions_created_at", "created_at"),
        Index("ix_transactions_trace_id", "trace_id"),
    )


class LedgerEntryRow(Base):
    """Comptabilité en double entrée : SUM(debit) = SUM(credit) doit être vérifiable."""

    __tablename__ = "ledger_entries"

    id: Mapped[UUID] = mapped_column(**_UUID_PK)
    transaction_id: Mapped[UUID] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    direction: Mapped[LedgerDirection] = mapped_column(
        _enum(LedgerDirection, "ledger_direction"), nullable=False
    )
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="amount_positive"),
        Index("ix_ledger_entries_transaction_id", "transaction_id"),
        Index("ix_ledger_entries_account_id", "account_id"),
    )
