"""Entités du domaine d'authentification (aucune dépendance framework)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class NewUser:
    full_name: str
    email: str
    phone: str
    password_hash: str  # argon2 ; jamais le mot de passe en clair


@dataclass(frozen=True)
class Profile:
    """Ce que le front a le droit de voir : jamais de hachage."""

    id: UUID
    full_name: str
    email: str
    phone: str | None
    iban_fake: str
    balance_cents: int


@dataclass(frozen=True)
class Credentials:
    profile: Profile
    password_hash: str
