"""Doubles de test : implémentations en mémoire des ports (LSP). Ni PostgreSQL ni HTTP."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.domain.errors import EmailAlreadyUsed, FaceCheckUnavailable, PhoneAlreadyUsed
from app.domain.models import Credentials, LedMode, NewUser, Profile


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


class FakeClock:
    def __init__(self) -> None:
        self._now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta


class FakeCamera:
    def __init__(self, broken: bool = False) -> None:
        self.broken = broken
        self.is_on = False

    async def start(self) -> None:
        if self.broken:
            raise FaceCheckUnavailable("caméra indisponible")
        self.is_on = True

    async def stop(self) -> None:
        self.is_on = False


class FakeFaceVerifier:
    def __init__(self, enrolled: set[str] | None = None, broken: bool = False) -> None:
        self.enrolled = enrolled or set()
        self.broken = broken
        self.present = True  # un visage conforme est devant la caméra

    async def verify(self, identifier: str) -> bool:
        if self.broken:
            raise FaceCheckUnavailable("agent hôte injoignable")
        return self.present and identifier in self.enrolled


class RecordingLed:
    def __init__(self, broken: bool = False) -> None:
        self.broken = broken
        self.modes: list[LedMode] = []

    async def set(self, mode: LedMode) -> None:
        if self.broken:
            raise ConnectionError("ESP8266 injoignable")
        self.modes.append(mode)
