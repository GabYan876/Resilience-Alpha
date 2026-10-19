"""Tests de l'adaptateur de persistance, sans base : structure du schéma.

Garde-fou contre la dérive entre les modèles SQLAlchemy et la migration initiale :
une migration en retard casse `reset_demo.sh`, donc la rejouabilité de la démo.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import BigInteger, String

from app.adapters.persistence.models import METADATA, AccountRow, TransactionRow

MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "services"
    / "db"
    / "migrations"
    / "versions"
    / "0001_socle_initial.py"
)

EXPECTED_TABLES = {"users", "merchants", "accounts", "transactions", "ledger_entries"}


def test_les_cinq_tables_du_socle_sont_declarees() -> None:
    assert set(METADATA.tables) == EXPECTED_TABLES


@pytest.mark.parametrize("table", sorted(EXPECTED_TABLES))
def test_la_migration_initiale_couvre_chaque_table(table: str) -> None:
    assert f'"{table}"' in MIGRATION.read_text(encoding="utf-8")


def test_les_montants_sont_des_entiers_64_bits() -> None:
    """Centimes en BIGINT : aucun type flottant sur de l'argent."""
    for column in (
        AccountRow.__table__.c.balance_cents,
        TransactionRow.__table__.c.amount_cents,
        METADATA.tables["ledger_entries"].c.amount_cents,
    ):
        assert isinstance(column.type, BigInteger)


def test_la_cle_d_idempotence_est_unique() -> None:
    column = TransactionRow.__table__.c.idempotency_key
    assert column.unique is True
    assert isinstance(column.type, String)


def test_les_comptes_ne_peuvent_pas_passer_en_negatif() -> None:
    constraints = {c.name for c in AccountRow.__table__.constraints}
    assert "ck_accounts_balance_non_negative" in constraints


def test_les_enums_portent_un_nom_postgresql_explicite() -> None:
    names = {
        METADATA.tables["users"].c.role.type.name,
        METADATA.tables["transactions"].c.status.type.name,
        METADATA.tables["ledger_entries"].c.direction.type.name,
    }
    assert names == {"user_role", "transaction_status", "ledger_direction"}


def test_les_roles_postgresql_de_durcissement_sont_crees_par_la_migration() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert "app_rw" in source and "app_ro" in source
    # `app_rw` ne doit jamais recevoir DELETE ni de droit DDL.
    assert "GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO {APP_RW}" in source
    granted = [line for line in source.splitlines() if "GRANT" in line and "REVOKE" not in line]
    assert granted
    assert all("DELETE" not in line and "TRUNCATE" not in line for line in granted)
