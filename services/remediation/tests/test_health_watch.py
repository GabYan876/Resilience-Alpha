import threading

from app.application.actions import RestartServiceAction
from app.application.health_watch import HealthWatchDetector
from app.application.pipeline import RemediationPipeline
from app.application.policy import KindBasedPolicy
from app.application.verifier import HealthAndProbeVerifier
from app.application.watcher import PipelineWatcher
from app.config import Settings
from app.domain.models import Anomaly, IncidentKind, IncidentStatus
from tests.fakes import (
    FakeContainerRestarter,
    FakeDetector,
    FakeHealthChecker,
    FakeTransactionProbe,
    InMemoryPublisher,
)


def test_single_missed_probe_is_not_a_crash():
    detector = HealthWatchDetector(FakeHealthChecker(False, True), ["api"], failure_threshold=3)
    assert detector.detect() is None
    assert detector.detect() is None


def test_consecutive_failures_report_a_crash():
    detector = HealthWatchDetector(FakeHealthChecker(False), ["api"], failure_threshold=3)
    assert detector.detect() is None
    assert detector.detect() is None
    anomaly = detector.detect()
    assert anomaly is not None
    assert anomaly.kind_hint is IncidentKind.CRASH
    assert anomaly.target_service == "api"
    assert anomaly.source == "healthcheck:api"


def test_failure_count_restarts_after_a_recovery():
    detector = HealthWatchDetector(
        FakeHealthChecker(False, False, True, False, False), ["api"], failure_threshold=3
    )
    assert [detector.detect() for _ in range(5)] == [None] * 5


def test_failure_count_restarts_after_a_report():
    detector = HealthWatchDetector(FakeHealthChecker(False), ["api"], failure_threshold=2)
    assert detector.detect() is None
    assert detector.detect() is not None
    assert detector.detect() is None  # la remédiation a la main, pas de second signalement


def crash_pipeline(detector, health, probe):
    restarter = FakeContainerRestarter()
    publisher = InMemoryPublisher()
    pipeline = RemediationPipeline(
        detector,
        KindBasedPolicy({IncidentKind.CRASH: [RestartServiceAction(restarter)]}),
        HealthAndProbeVerifier(health, probe),
        publisher,
    )
    return pipeline, restarter, publisher


def test_crash_is_restarted_without_blocking_anyone_and_proven_by_transaction():
    anomaly = Anomaly(score=1.0, source="healthcheck:api", kind_hint=IncidentKind.CRASH)
    pipeline, restarter, publisher = crash_pipeline(
        FakeDetector([anomaly]), FakeHealthChecker(True), FakeTransactionProbe(True)
    )
    incident = pipeline.run_once()
    assert incident is not None and incident.status is IncidentStatus.RESOLVED
    assert restarter.restarted == ["api"]
    assert publisher.names == [
        "incident.detected",
        "decision.made",
        "action.executed",
        "verification.completed",
        "incident.resolved",
    ]


def test_crash_is_not_resolved_if_the_probe_transaction_fails():
    anomaly = Anomaly(score=1.0, source="healthcheck:api", kind_hint=IncidentKind.CRASH)
    pipeline, _, _ = crash_pipeline(
        FakeDetector([anomaly]), FakeHealthChecker(True), FakeTransactionProbe(False)
    )
    incident = pipeline.run_once()
    assert incident is not None and incident.status is IncidentStatus.FAILED


class BlockingDetector:
    """Détecteur dont le passage reste suspendu : simule un incident en cours de traitement."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = 0

    def detect(self) -> Anomaly | None:
        self.calls += 1
        self.entered.set()
        self.release.wait(timeout=5)
        return None


def test_run_once_yields_while_an_incident_is_being_handled():
    detector = BlockingDetector()
    pipeline, _, _ = crash_pipeline(detector, FakeHealthChecker(True), FakeTransactionProbe(True))
    first = threading.Thread(target=pipeline.run_once)
    first.start()
    assert detector.entered.wait(timeout=5)
    assert pipeline.run_once() is None  # ne bloque pas et ne sonde pas pendant l'incident
    assert detector.calls == 1
    detector.release.set()
    first.join(timeout=5)


def test_push_handling_waits_for_the_running_incident():
    detector = BlockingDetector()
    pipeline, restarter, _ = crash_pipeline(
        detector, FakeHealthChecker(True), FakeTransactionProbe(True)
    )
    first = threading.Thread(target=pipeline.run_once)
    first.start()
    assert detector.entered.wait(timeout=5)

    pushed = threading.Thread(
        target=pipeline.handle,
        args=(Anomaly(score=1.0, source="push", kind_hint=IncidentKind.CRASH),),
    )
    pushed.start()
    pushed.join(timeout=0.2)
    assert pushed.is_alive() and restarter.restarted == []  # file d'attente, pas de concurrence
    detector.release.set()
    first.join(timeout=5)
    pushed.join(timeout=5)
    assert restarter.restarted == ["api"]


def test_watcher_runs_the_pipeline_until_stopped():
    class CountingPipeline:
        def __init__(self) -> None:
            self.calls = 0
            self.called = threading.Event()

        def run_once(self) -> None:
            self.calls += 1
            self.called.set()
            if self.calls == 1:
                raise RuntimeError("panne isolée")  # ne doit pas tuer la boucle

    pipeline = CountingPipeline()
    watcher = PipelineWatcher(pipeline, interval_s=0.01)  # type: ignore[arg-type]
    watcher.start()
    deadline_calls = 3
    for _ in range(500):
        if pipeline.calls >= deadline_calls:
            break
        threading.Event().wait(0.01)
    watcher.stop()
    assert pipeline.calls >= deadline_calls


def test_watch_is_disabled_by_default_and_enabled_from_env(monkeypatch):
    base = dict(
        api_base_url="http://api",
        api_health_url="http://api/health",
        docker_proxy_url="http://proxy",
        ingest_token="t",
        probe_token="",
    )
    assert Settings(**base).watch_interval_s == 0.0
    monkeypatch.setenv("REMEDIATION_INGEST_TOKEN", "t")
    monkeypatch.setenv("WATCH_INTERVAL_S", "2")
    monkeypatch.setenv("WATCH_FAILURES", "4")
    settings = Settings.from_env()
    assert (settings.watch_interval_s, settings.watch_failures) == (2.0, 4)
