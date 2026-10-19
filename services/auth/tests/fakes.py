"""Doubles de test : implémentations en mémoire des ports (LSP). Ni PostgreSQL ni HTTP."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.domain.errors import EmailAlreadyUsed, PhoneAlreadyUsed
from app.domain.models import Credentials, NewUser, Profile


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.by_email: dict[str, Credentials] = {}
        self.balances: list[int] = []

    async def create(self, user: NewUser, welcome_balance_cents: int) -> Profile:
        if user.email in self.by_email:
            raise EmailAlreadyUsed("cette adresse e-mail est déjà utilisée")
        if any(c.profile.phone == user.phone for c in self.by_email.values()):
            raise PhoneAlreadyUsed("ce numéro de téléphone est déjà utilisé")
        profile = Profile(
            id=uuid4(),
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            iban_fake=f"FR76{len(self.by_email):023d}",
            balance_cents=welcome_balance_cents,
        )
        self.by_email[user.email] = Credentials(profile, user.password_hash)
        self.balances.append(welcome_balance_cents)
        return profile

    async def find_by_email(self, email: str) -> Credentials | None:
        return self.by_email.get(email)


class PlainHasher:
    """Hachage trivial : les tests de cas d'usage ne paient pas le coût d'argon2."""

    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{password}"


class StaticTokenIssuer:
    def issue(self, user_id: UUID) -> str:
        return f"token-{user_id}"


class RecordingPublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def publish(self, event: str, trace_id: str, **data: object) -> None:
        self.events.append((event, data))


class HealthyProbe:
    def __init__(self, up: bool = True) -> None:
        self._up = up

    async def ping(self) -> bool:
        return self._up
