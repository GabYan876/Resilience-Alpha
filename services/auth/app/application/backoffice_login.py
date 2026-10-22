"""Connexion du back-office : identifiant → visage (1:1) → mot de passe, blocage par identifiant.

La LED reflète l'état (consigne 1). Échec fermé : caméra ou agent en panne = pas d'accès.
"""

from __future__ import annotations

import asyncio
import hashlib
from uuid import uuid4

from app.application.use_cases import AuthResult
from app.domain.errors import (
    AccountLocked,
    FaceCheckUnavailable,
    FaceNotRecognized,
    FaceNotVerified,
    InvalidCredentials,
)
from app.domain.models import LedMode, LockoutPolicy
from app.domain.ports import (
    CameraControl,
    Clock,
    EventPublisher,
    FaceSessionStore,
    FaceVerifier,
    LockoutStore,
    PasswordHasher,
    StatusLed,
    TokenIssuer,
    UserRepository,
)


class BackOfficeLogin:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenIssuer,
        camera: CameraControl,
        faces: FaceVerifier,
        led: StatusLed,
        lockouts: LockoutStore,
        sessions: FaceSessionStore,
        clock: Clock,
        publisher: EventPublisher,
        policy: LockoutPolicy | None = None,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        self._camera = camera
        self._faces = faces
        self._led = led
        self._lockouts = lockouts
        self._sessions = sessions
        self._clock = clock
        self._publisher = publisher
        self._policy = policy or LockoutPolicy()

    async def start(self, identifier: str) -> None:
        """Étape 1 : caméra, comparaison au gabarit, LED. Lève une `DomainError` sinon."""
        trace_id = uuid4().hex
        await self._ensure_not_locked(identifier, trace_id)
        await self._set_led(LedMode.OFF, trace_id)
        try:
            await self._camera.start()
            recognized = await self._faces.verify(identifier)
        except FaceCheckUnavailable:
            self._emit("auth.face.unavailable", trace_id, identifier)
            raise  # ni échec compté ni repli sur le mot de passe seul
        finally:
            await self._stop_camera(trace_id)

        if not recognized:
            await self._register_failure(identifier, trace_id)
            await self._set_led(LedMode.RED_SOLID, trace_id)
            self._emit("auth.face.rejected", trace_id, identifier)
            raise FaceNotRecognized("visage non reconnu")

        now = self._clock.now()
        await self._sessions.grant(identifier, now + self._policy.face_validity)
        await self._set_led(LedMode.GREEN_BLINK, trace_id)
        self._emit("auth.face.recognized", trace_id, identifier)

    async def submit_password(self, identifier: str, password: str) -> AuthResult:
        """Étape 2 : mot de passe, uniquement après un visage reconnu (usage unique)."""
        trace_id = uuid4().hex
        await self._ensure_not_locked(identifier, trace_id)
        if not await self._sessions.consume(identifier, self._clock.now()):
            self._emit("auth.password.refused_no_face", trace_id, identifier)
            raise FaceNotVerified("reconnaissance du visage requise")

        found = await self._users.find_by_email(identifier)
        valid = found is not None and await asyncio.to_thread(
            self._hasher.verify, password, found.password_hash
        )
        if not valid or found is None:
            await self._register_failure(identifier, trace_id)
            await self._set_led(LedMode.RED_BLINK, trace_id)
            self._emit("auth.password.failed", trace_id, identifier)
            raise InvalidCredentials("identifiant ou mot de passe incorrect")

        await self._lockouts.clear(identifier)
        await self._set_led(LedMode.GREEN_SOLID, trace_id)
        self._emit("auth.login.succeeded", trace_id, identifier)
        return AuthResult(self._tokens.issue(found.profile.id), found.profile)

    async def _ensure_not_locked(self, identifier: str, trace_id: str) -> None:
        now = self._clock.now()
        record = await self._lockouts.get(identifier)
        if record.is_locked(now) and record.locked_until is not None:
            self._emit("auth.locked.refused", trace_id, identifier)
            raise AccountLocked(int((record.locked_until - now).total_seconds()) + 1)

    async def _register_failure(self, identifier: str, trace_id: str) -> None:
        now = self._clock.now()
        record = (await self._lockouts.get(identifier)).register_failure(now, self._policy)
        await self._lockouts.save(record)
        if record.locked_until is not None:
            self._emit("auth.locked", trace_id, identifier)

    async def _stop_camera(self, trace_id: str) -> None:
        try:
            await self._camera.stop()
        except Exception:  # noqa: BLE001 - l'arrêt ne doit pas masquer la décision
            self._publisher.publish("auth.camera.stop_failed", trace_id)

    async def _set_led(self, mode: LedMode, trace_id: str) -> None:
        try:
            await self._led.set(mode)
        except Exception:  # noqa: BLE001 - la LED est un retour visuel, pas une condition d'accès
            self._publisher.publish("auth.led.unavailable", trace_id, mode=mode.value)

    def _emit(self, event: str, trace_id: str, identifier: str) -> None:
        # Empreinte courte : corrélable dans Loki sans écrire l'identifiant en clair.
        digest = hashlib.sha256(identifier.encode()).hexdigest()[:12]
        self._publisher.publish(event, trace_id, identifier_hash=digest)
