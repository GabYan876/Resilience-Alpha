"""Fakes en mémoire des ports (substituables aux adaptateurs de prod, LSP)."""

from __future__ import annotations

from collections.abc import Iterable

from app.domain.models import Anomaly, PipelineEvent


class FakeDetector:
    def __init__(self, anomalies: Iterable[Anomaly | None] = ()) -> None:
        self._queue = list(anomalies)

    def detect(self) -> Anomaly | None:
        return self._queue.pop(0) if self._queue else None


class FakeContainerRestarter:
    def __init__(self) -> None:
        self.restarted: list[str] = []

    def restart(self, service: str) -> None:
        self.restarted.append(service)


class FakeDatabaseRestorer:
    def __init__(self) -> None:
        self.restores = 0
        self.before = None

    def restore_latest(self, before) -> None:
        self.restores += 1
        self.before = before


class FakeServiceScaler:
    def __init__(self) -> None:
        self.scaled: list[tuple[str, int]] = []

    def scale(self, service: str, replicas: int) -> None:
        self.scaled.append((service, replicas))


class FakeIpBlocker:
    def __init__(self) -> None:
        self.blocked: set[str] = set()

    def block(self, ip: str) -> None:
        self.blocked.add(ip)

    def unblock(self, ip: str) -> None:
        self.blocked.discard(ip)


class FakeSecretRotator:
    def __init__(self) -> None:
        self.rotated: list[str] = []

    def rotate(self, secret_name: str) -> None:
        self.rotated.append(secret_name)


class FakeHealthChecker:
    """Retourne les résultats dans l'ordre ; le dernier est répété indéfiniment."""

    def __init__(self, *results: bool) -> None:
        self._results = list(results) or [True]

    def is_healthy(self, service: str) -> bool:
        return self._results.pop(0) if len(self._results) > 1 else self._results[0]


class FakeTransactionProbe:
    def __init__(self, *results: bool | Exception) -> None:
        self._results = list(results) or [True]
        self.calls = 0

    def run(self) -> bool:
        self.calls += 1
        result = self._results.pop(0) if len(self._results) > 1 else self._results[0]
        if isinstance(result, Exception):
            raise result
        return result


class InMemoryPublisher:
    def __init__(self) -> None:
        self.events: list[PipelineEvent] = []

    def publish(self, event: PipelineEvent) -> None:
        self.events.append(event)

    @property
    def names(self) -> list[str]:
        return [e.event for e in self.events]


class FakeSubjectBlocker:
    def __init__(self) -> None:
        self.blocked: set[str] = set()

    def block(self, subject: str) -> None:
        self.blocked.add(subject)

    def unblock(self, subject: str) -> None:
        self.blocked.discard(subject)
