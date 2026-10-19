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
