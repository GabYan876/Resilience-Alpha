"""Entités du domaine d'authentification (aucune dépendance framework)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
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


class LedMode(StrEnum):
    """Modes de la LED bicolore de l'ESP8266 (durées gérées par le firmware)."""

    OFF = "off"
    GREEN_BLINK = "green_blink"
    GREEN_SOLID = "green_solid"
    RED_BLINK = "red_blink"
    RED_SOLID = "red_solid"


@dataclass(frozen=True)
class LockoutPolicy:
    """2 échecs consécutifs (1 essai + 1 reprise) bloquent l'identifiant 5 minutes."""

    max_failures: int = 2
    lock_duration: timedelta = timedelta(minutes=5)
    face_validity: timedelta = timedelta(minutes=2)  # délai pour saisir le mot de passe


@dataclass(frozen=True)
class LockoutRecord:
    """Échecs consécutifs d'un identifiant (et non d'une IP : voir arbitrage du 20/10)."""

    identifier: str
    failures: int = 0
    locked_until: datetime | None = None

    def is_locked(self, now: datetime) -> bool:
        return self.locked_until is not None and now < self.locked_until

    def register_failure(self, now: datetime, policy: LockoutPolicy) -> LockoutRecord:
        failures = self.failures + 1
        if failures >= policy.max_failures:
            # Le compteur repart à 0 : le schéma se répète à la sortie du blocage.
            return LockoutRecord(self.identifier, 0, now + policy.lock_duration)
        return LockoutRecord(self.identifier, failures, None)
