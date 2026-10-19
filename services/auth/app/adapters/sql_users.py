"""Dépôt d'utilisateurs sur PostgreSQL (tables `users` et `accounts` du socle de données).

SQL explicite plutôt qu'un second jeu de modèles ORM : le schéma appartient à
`services/db` (Alembic) et cette copie divergerait. Rôle `app_rw` : pas de DDL.
"""

from __future__ import annotations

import secrets
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.errors import EmailAlreadyUsed, PhoneAlreadyUsed
from app.domain.models import Credentials, NewUser, Profile

_INSERT_USER = text(
    "INSERT INTO users (id, email, password_hash, full_name, phone, role) "
    "VALUES (:id, :email, :password_hash, :full_name, :phone, 'customer')"
)
_INSERT_ACCOUNT = text(
    "INSERT INTO accounts (id, user_id, iban_fake, balance_cents, currency) "
    "VALUES (:id, :user_id, :iban, :balance, 'EUR')"
)
# Seuls les clients se connectent ici : la sonde et les marchands n'ont pas de session.
_FIND_BY_EMAIL = text(
    "SELECT u.id, u.full_name, u.email, u.phone, u.password_hash, a.iban_fake, a.balance_cents "
    "FROM users u JOIN accounts a ON a.user_id = u.id "
    "WHERE u.email = :email AND u.role = 'customer' ORDER BY a.iban_fake LIMIT 1"
)


def _new_iban() -> str:
    """IBAN fictif de laboratoire : 25 chiffres aléatoires, aucune donnée bancaire réelle."""
    return "FR76" + "".join(secrets.choice("0123456789") for _ in range(23))


class SqlUserRepository:
    """Implémente le port `UserRepository`."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create(self, user: NewUser, welcome_balance_cents: int) -> Profile:
        user_id, iban = uuid4(), _new_iban()
        try:
            async with self._engine.begin() as connection:  # utilisateur + compte, ou rien
                await connection.execute(
                    _INSERT_USER,
                    {
                        "id": user_id,
                        "email": user.email,
                        "password_hash": user.password_hash,
                        "full_name": user.full_name,
                        "phone": user.phone,
                    },
                )
                await connection.execute(
                    _INSERT_ACCOUNT,
                    {
                        "id": uuid4(),
                        "user_id": user_id,
                        "iban": iban,
                        "balance": welcome_balance_cents,
                    },
                )
        except IntegrityError as exc:
            raise _duplicate(exc) from exc
        return Profile(
            id=user_id,
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            iban_fake=iban,
            balance_cents=welcome_balance_cents,
        )

    async def find_by_email(self, email: str) -> Credentials | None:
        async with self._engine.connect() as connection:
            row = (await connection.execute(_FIND_BY_EMAIL, {"email": email})).first()
        if row is None:
            return None
        return Credentials(
            profile=Profile(
                id=UUID(str(row.id)),
                full_name=row.full_name,
                email=row.email,
                phone=row.phone,
                iban_fake=row.iban_fake,
                balance_cents=row.balance_cents,
            ),
            password_hash=row.password_hash,
        )


def _duplicate(exc: IntegrityError) -> Exception:
    """Traduit la violation d'unicité en erreur métier ; toute autre reste une panne."""
    message = str(exc.orig)
    if "uq_users_phone" in message:
        return PhoneAlreadyUsed("ce numéro de téléphone est déjà utilisé")
    if "uq_users_email" in message:
        return EmailAlreadyUsed("cette adresse e-mail est déjà utilisée")
    return exc
