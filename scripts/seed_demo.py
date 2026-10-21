#!/usr/bin/env python3
"""Jeu de données de démonstration, 100 % fictif et rejouable.

Idempotent : chaque exécution remet les soldes aux valeurs de référence (UPSERT).
C'est ce qui permet d'enchaîner cinq démonstrations sans intervention humaine.

Le compte de sonde `probe@resilience.local` / `TEST-0001` est obligatoire : le
moteur de remédiation prouve la reprise en jouant une vraie transaction depuis
ce compte (voir `services/remediation/app/adapters/api_probe.py`). Sans recharge
du solde, la sonde finirait par échouer pour solde insuffisant et l'on croirait
à une panne du système.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID, uuid5

_HERE = Path(__file__).resolve().parent


def _add_api_package_to_path() -> None:
    """`services/api` dans le dépôt, `/app` dans l'image Docker."""
    for candidate in (_HERE.parent / "services" / "api", _HERE.parent):
        if (candidate / "app" / "adapters" / "persistence" / "models.py").is_file():
            sys.path.insert(0, str(candidate))
            return
    raise RuntimeError("paquet `app` introuvable")


_add_api_package_to_path()

from app.adapters.persistence.engine import build_engine, build_session_factory
from app.adapters.persistence.models import AccountRow, MerchantRow, UserRow
from app.domain.models import UserRole
from argon2 import PasswordHasher
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

# Namespace fixe : les mêmes identifiants à chaque passage, donc des URL stables
# pour le dashboard et les captures de la vidéo.
_NAMESPACE = UUID("00000000-0000-0000-0000-00000000a1fa")

PROBE_EMAIL = "probe@resilience.local"
PROBE_IBAN = "TEST-0001"
PROBE_COUNTERPARTY_IBAN = "TEST-0002"


def _uid(label: str) -> UUID:
    return uuid5(_NAMESPACE, label)


def _seed_password() -> str:
    """Mot de passe de laboratoire. Aucun secret réel : valeur fictive, hachée en argon2."""
    return os.environ.get("SEED_PASSWORD", "demo-only-not-a-secret")


def _probe_balance_cents() -> int:
    return int(os.environ.get("PROBE_BALANCE_CENTS", "1000000"))


def _users(password_hash: str) -> list[dict[str, object]]:
    return [
        {
            "id": _uid("user:probe"),
            "full_name": "Compte de sonde",
            "email": PROBE_EMAIL,
            "password_hash": password_hash,
            "role": UserRole.PROBE,
        },
        {
            "id": _uid("user:alice"),
            "full_name": "Alice Martin",
            "email": "alice@resilience.local",
            "password_hash": password_hash,
            "role": UserRole.CUSTOMER,
        },
        {
            "id": _uid("user:bob"),
            "full_name": "Bob Durand",
            "email": "bob@resilience.local",
            "password_hash": password_hash,
            "role": UserRole.CUSTOMER,
        },
        {
            "id": _uid("user:shop"),
            "full_name": "Boutique Alpha",
            "email": "shop@resilience.local",
            "password_hash": password_hash,
            "role": UserRole.MERCHANT,
        },
    ]


def _merchants(api_key_hash: str) -> list[dict[str, object]]:
    return [
        {
            "id": _uid("merchant:shop"),
            "name": "Boutique Alpha",
            "mcc": "5732",
            "api_key_hash": api_key_hash,
        },
        {
            "id": _uid("merchant:cafe"),
            "name": "Café Résilience",
            "mcc": "5814",
            "api_key_hash": api_key_hash,
        },
    ]


def _accounts() -> list[dict[str, object]]:
    return [
        # Comptes de la sonde de reprise : rechargés à chaque reset.
        {
            "id": _uid("account:probe"),
            "user_id": _uid("user:probe"),
            "iban_fake": PROBE_IBAN,
            "balance_cents": _probe_balance_cents(),
            "currency": "EUR",
        },
        {
            "id": _uid("account:probe-counterparty"),
            "user_id": _uid("user:probe"),
            "iban_fake": PROBE_COUNTERPARTY_IBAN,
            "balance_cents": 0,
            "currency": "EUR",
        },
        {
            "id": _uid("account:alice"),
            "user_id": _uid("user:alice"),
            "iban_fake": "FR7630001007941234567890185",
            "balance_cents": 250_000,
            "currency": "EUR",
        },
        {
            "id": _uid("account:bob"),
            "user_id": _uid("user:bob"),
            "iban_fake": "FR7630001007941234567890186",
            "balance_cents": 120_000,
            "currency": "EUR",
        },
        {
            "id": _uid("account:shop"),
            "user_id": _uid("user:shop"),
            "iban_fake": "FR7630001007941234567890187",
            "balance_cents": 500_000,
            "currency": "EUR",
        },
    ]


async def seed() -> None:
    database_url = os.environ.get("DATABASE_URL_ADMIN") or os.environ["DATABASE_URL"]
    hasher = PasswordHasher()
    password_hash = hasher.hash(_seed_password())
    api_key_hash = hasher.hash("fake-api-key-for-demo")

    engine = build_engine(database_url, pool_size=1)
    session_factory = build_session_factory(engine)
    try:
        async with session_factory() as session:
            users = insert(UserRow).values(_users(password_hash))
            await session.execute(
                users.on_conflict_do_update(
                    index_elements=[UserRow.email],
                    set_={
                        "password_hash": users.excluded.password_hash,
                        "full_name": users.excluded.full_name,
                    },
                )
            )
            merchants = insert(MerchantRow).values(_merchants(api_key_hash))
            await session.execute(
                merchants.on_conflict_do_nothing(index_elements=[MerchantRow.id])
            )
            accounts = insert(AccountRow).values(_accounts())
            await session.execute(
                # La recharge des soldes est le cœur de la rejouabilité.
                accounts.on_conflict_do_update(
                    index_elements=[AccountRow.iban_fake],
                    set_={
                        "balance_cents": accounts.excluded.balance_cents,
                        "currency": accounts.excluded.currency,
                    },
                )
            )
            await session.commit()

            balance = await session.execute(
                text("SELECT balance_cents FROM accounts WHERE iban_fake = :iban"),
                {"iban": PROBE_IBAN},
            )
            print(
                f"seed terminé : sonde {PROBE_IBAN} rechargée à {balance.scalar_one()} centimes"
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
