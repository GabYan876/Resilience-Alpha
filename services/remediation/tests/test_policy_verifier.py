from app.application.policy import KindBasedPolicy
from app.application.verifier import HealthAndProbeVerifier
from app.domain.models import ActionResult, Anomaly, Incident, IncidentKind
from tests.fakes import FakeHealthChecker, FakeTransactionProbe


def make_incident(kind: IncidentKind) -> Incident:
    return Incident(Anomaly(score=0.9, source="test", kind_hint=kind))


class StubAction:
    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, incident: Incident) -> ActionResult:
        return ActionResult(self.name, True)


def test_policy_distinguishes_availability_from_compromise():
    restart, rotate = StubAction("restart"), StubAction("rotate")
    policy = KindBasedPolicy(
        {IncidentKind.AVAILABILITY: [restart], IncidentKind.COMPROMISE: [rotate]}
    )
    assert policy.decide(make_incident(IncidentKind.AVAILABILITY)) == [restart]
    assert policy.decide(make_incident(IncidentKind.COMPROMISE)) == [rotate]


def test_policy_returns_nothing_for_unknown_kind():
    assert KindBasedPolicy({}).decide(make_incident(IncidentKind.AVAILABILITY)) == ()


def test_verifier_requires_health_and_transaction():
    verifier = HealthAndProbeVerifier(FakeHealthChecker(True), FakeTransactionProbe(True))
    assert verifier.verify(make_incident(IncidentKind.AVAILABILITY)).recovered


def test_verifier_unhealthy_api_skips_probe():
    probe = FakeTransactionProbe(True)
    report = HealthAndProbeVerifier(FakeHealthChecker(False), probe).verify(
        make_incident(IncidentKind.AVAILABILITY)
    )
    assert not report.recovered
    assert probe.calls == 0


def test_verifier_healthy_api_is_not_enough():
    """Un conteneur qui répond ne prouve rien si la transaction échoue."""
    report = HealthAndProbeVerifier(FakeHealthChecker(True), FakeTransactionProbe(False)).verify(
        make_incident(IncidentKind.AVAILABILITY)
    )
    assert report.api_healthy and not report.recovered


def test_verifier_probe_exception_is_a_failure():
    probe = FakeTransactionProbe(RuntimeError("boom"))
    report = HealthAndProbeVerifier(FakeHealthChecker(True), probe).verify(
        make_incident(IncidentKind.AVAILABILITY)
    )
    assert not report.recovered


class FakeClock:
    """Horloge manuelle : `sleep` avance le temps, aucun test n'attend réellement."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def make_waiting_verifier(health, probe, clock, wait_s=10.0):
    return HealthAndProbeVerifier(
        health,
        probe,
        health_wait_s=wait_s,
        poll_interval_s=1.0,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )


def test_verifier_waits_for_api_to_come_back_after_restart():
    """Le redémarrage rend la main avant que l'API soit prête : pas d'échec prématuré."""
    clock = FakeClock()
    probe = FakeTransactionProbe(True)
    verifier = make_waiting_verifier(FakeHealthChecker(False, False, False, True), probe, clock)
    report = verifier.verify(make_incident(IncidentKind.AVAILABILITY))
    assert report.recovered
    assert clock.sleeps == [1.0, 1.0, 1.0]
    assert probe.calls == 1


def test_verifier_gives_up_when_api_never_comes_back():
    clock = FakeClock()
    probe = FakeTransactionProbe(True)
    verifier = make_waiting_verifier(FakeHealthChecker(False), probe, clock, wait_s=5.0)
    report = verifier.verify(make_incident(IncidentKind.AVAILABILITY))
    assert not report.recovered and not report.api_healthy
    assert clock.now == 5.0
    assert probe.calls == 0


def test_verifier_does_not_sleep_when_api_is_already_healthy():
    clock = FakeClock()
    verifier = make_waiting_verifier(FakeHealthChecker(True), FakeTransactionProbe(True), clock)
    assert verifier.verify(make_incident(IncidentKind.AVAILABILITY)).recovered
    assert clock.sleeps == []
