"""Socle initial : utilisateurs, marchands, comptes, transactions, grand livre, rôles

Revision ID: 0001_socle_initial
Revises:
Create Date: 2026-10-19

Durcissement : deux rôles PostgreSQL applicatifs sont créés ici.
- `app_rw` : SELECT / INSERT / UPDATE, aucun DDL, aucun DELETE -> utilisé par l'API ;
- `app_ro` : SELECT seul -> destiné à l'assistant RAG.
Une injection SQL réussie contre l'API ne peut donc ni supprimer une table ni
effacer une ligne : au pire elle lit et écrit des données fictives.
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0001_socle_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_RW = "app_rw"
APP_RO = "app_ro"

USER_ROLE = postgresql.ENUM(
    "customer", "merchant", "probe", "admin", name="user_role", create_type=False
)
TRANSACTION_STATUS = postgresql.ENUM(
    "pending",
    "settled",
    "failed",
    "rejected",
    name="transaction_status",
    create_type=False,
)
LEDGER_DIRECTION = postgresql.ENUM(
    "debit", "credit", name="ledger_direction", create_type=False
)


def _create_role(role: str, password_env: str) -> None:
    """Crée le rôle si absent, sans jamais écrire le mot de passe dans le SQL journalisé.

    Le secret transite par un paramètre lié puis par un réglage de session
    (`current_setting`), pas par une chaîne SQL interpolée.
    """
    if context.is_offline_mode():
        # `alembic upgrade head --sql` sert à relire le DDL : on n'y écrit jamais
        # de mot de passe. Les rôles ne se créent qu'en mode connecté.
        op.execute(f"-- rôle {role} : créé uniquement en mode connecté")
        return
    password = os.environ.get(password_env, "")
    if not password:
        raise RuntimeError(f"{password_env} doit être défini pour créer le rôle {role}")
    bind = op.get_bind()
    guc = f"resilience.{role}_password"
    bind.execute(
        sa.text("SELECT set_config(:guc, :pwd, false)"), {"guc": guc, "pwd": password}
    )
    bind.execute(
        sa.text(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                    EXECUTE format(
                        'CREATE ROLE {role} LOGIN PASSWORD %L',
                        current_setting('{guc}')
                    );
                ELSE
                    EXECUTE format(
                        'ALTER ROLE {role} LOGIN PASSWORD %L',
                        current_setting('{guc}')
                    );
                END IF;
            END
            $$;
            """)
    )
    bind.execute(sa.text("SELECT set_config(:guc, '', false)"), {"guc": guc})


def _drop_role(role: str) -> None:
    op.execute(f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                EXECUTE 'DROP OWNED BY {role}';
                EXECUTE 'DROP ROLE {role}';
            END IF;
        END
        $$;
        """)


def _create_tables() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),  # argon2
        sa.Column(
            "role",
            sa.Enum(
                "customer",
                "merchant",
                "probe",
                "admin",
                name="user_role",
                native_enum=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "merchants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("mcc", sa.String(length=4), nullable=False),
        sa.Column("api_key_hash", sa.String(length=255), nullable=False),
        sa.CheckConstraint("mcc ~ '^[0-9]{4}$'", name="mcc_format"),
        sa.PrimaryKeyConstraint("id", name="pk_merchants"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("iban_fake", sa.String(length=34), nullable=False),
        sa.Column("balance_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.CheckConstraint("balance_cents >= 0", name="balance_non_negative"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_accounts_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_accounts"),
        sa.UniqueConstraint("iban_fake", name="uq_accounts_iban_fake"),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_from", sa.Uuid(), nullable=False),
        sa.Column("account_to", sa.Uuid(), nullable=False),
        sa.Column(
            "amount_cents", sa.BigInteger(), nullable=False
        ),  # centimes, jamais de float
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "settled",
                "failed",
                "rejected",
                name="transaction_status",
                native_enum=True,
            ),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("amount_cents > 0", name="amount_positive"),
        sa.CheckConstraint("account_from <> account_to", name="distinct_accounts"),
        sa.ForeignKeyConstraint(
            ["account_from"],
            ["accounts.id"],
            name="fk_transactions_account_from_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["account_to"], ["accounts.id"], name="fk_transactions_account_to_accounts"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
        # Clé d'idempotence unique : rejouer la sonde ne débite jamais deux fois.
        sa.UniqueConstraint("idempotency_key", name="uq_transactions_idempotency_key"),
    )
    op.create_index("ix_transactions_created_at", "transactions", ["created_at"])
    op.create_index("ix_transactions_trace_id", "transactions", ["trace_id"])

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column(
            "direction",
            sa.Enum("debit", "credit", name="ledger_direction", native_enum=True),
            nullable=False,
        ),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("amount_cents > 0", name="amount_positive"),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_ledger_entries_account_id_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name="fk_ledger_entries_transaction_id_transactions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ledger_entries"),
    )
    op.create_index(
        "ix_ledger_entries_transaction_id", "ledger_entries", ["transaction_id"]
    )
    op.create_index("ix_ledger_entries_account_id", "ledger_entries", ["account_id"])


def _grant_privileges() -> None:
    # PostgreSQL < 15 accorde CREATE sur `public` à tout le monde : on le retire.
    op.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")

    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_RW}")
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO {APP_RW}"
    )
    # Le grand livre est en ajout seul : une écriture passée ne se réécrit pas.
    op.execute(f"REVOKE UPDATE ON TABLE ledger_entries FROM {APP_RW}")
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE ON TABLES TO {APP_RW}"
    )

    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_RO}")
    op.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {APP_RO}")
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {APP_RO}"
    )


def upgrade() -> None:
    _create_role(APP_RW, "APP_RW_PASSWORD")
    _create_role(APP_RO, "APP_RO_PASSWORD")
    _create_tables()
    _grant_privileges()


def downgrade() -> None:
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM {APP_RO}"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"REVOKE SELECT, INSERT, UPDATE ON TABLES FROM {APP_RW}"
    )
    op.drop_table("ledger_entries")
    op.drop_table("transactions")
    op.drop_table("accounts")
    op.drop_table("merchants")
    op.drop_table("users")
    for enum in (LEDGER_DIRECTION, TRANSACTION_STATUS, USER_ROLE):
        enum.drop(op.get_bind(), checkfirst=True)
    _drop_role(APP_RO)
    _drop_role(APP_RW)
