"""Profil utilisateur : nom complet et téléphone (inscription depuis le front Pay-Now)

Revision ID: 0002_profil_utilisateur
Revises: 0001_socle_initial
Create Date: 2026-10-19

Les droits `app_rw` / `app_ro` couvrent déjà ces colonnes (privilèges au niveau table).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_profil_utilisateur"
down_revision: str | None = "0001_socle_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # server_default '' : les comptes déjà présents (seed) restent valides.
    op.add_column(
        "users", sa.Column("full_name", sa.String(120), nullable=False, server_default="")
    )
    op.add_column("users", sa.Column("phone", sa.String(20), nullable=True))
    op.create_unique_constraint("uq_users_phone", "users", ["phone"])


def downgrade() -> None:
    op.drop_constraint("uq_users_phone", "users", type_="unique")
    op.drop_column("users", "phone")
    op.drop_column("users", "full_name")
