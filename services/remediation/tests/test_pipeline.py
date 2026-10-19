from app.application.actions import (
    BlockIpAction,
    RestartServiceAction,
    RotateSecretAction,
)
from app.application.pipeline import RemediationPipeline
from app.application.policy import KindBasedPolicy
from app.application.verifier import HealthAndProbeVerifier
from app.domain.models import ActionResult, Anomaly, Incident, IncidentKind, IncidentStatus
from tests.fakes import (
    FakeContainerRestarter,
    FakeDetector,
    FakeHealthChecker,
    FakeIpBlocker,
    FakeSecretRotator,
    FakeTransactionProbe,
    InMemoryPublisher,
)

ATTACKER = "192.168.137.50"


def anomaly(kind: IncidentKind) -> Anomaly:
    return Anomaly(score=0.95, source="test", kind_hint=kind, attacker_ip=ATTACKER)


class Setup:
    def __init__(self, detector, health, probe, max_attempts=2) -> None:
        self.blocker = FakeIpBlocker()
        self.restarter = FakeContainerRestarter()
        self.rotator = FakeSecretRotator()
        self.publisher = InMemoryPublisher()
        policy = KindBasedPolicy(
            {
                IncidentKind.AVAILABILITY: [
                    BlockIpAction(self.blocker),
                    RestartServiceAction(self.restarter),
                ],
                IncidentKind.COMPROMISE: [
                    BlockIpAction(self.blocker),
                    RotateSecretAction(self.rotator, "db_password"),
                ],
            }
        )
        self.pipeline = RemediationPipeline(
            detector,
            policy,
            HealthAndProbeVerifier(health, probe),
            self.publisher,
            max_attempts=max_attempts,
        )


def test_no_anomaly_does_nothing():
    s = Setup(FakeDetector(), FakeHealthChecker(True), FakeTransactionProbe(True))
    assert s.pipeline.run_once() is None
    assert s.publisher.events == []


def test_flood_is_remediated_and_proven_by_transaction():
    s = Setup(
        FakeDetector([anomaly(IncidentKind.AVAILABILITY)]),
        FakeHealthChecker(True),
        FakeTransactionProbe(True),
    )
    incident = s.pipeline.run_once()

    assert incident.status is IncidentStatus.RESOLVED
    assert s.blocker.blocked == {ATTACKER}
    assert s.restarter.restarted == ["api"]
    assert s.rotator.rotated == []  # disponibilité : pas de rotation de secrets
    assert s.publisher.names == [
        "incident.detected",
        "decision.made",
        "action.executed",
        "action.executed",
        "verification.completed",
        "incident.resolved",
    ]


def test_compromise_rotates_secret_without_restart():
    s = Setup(
        FakeDetector([anomaly(IncidentKind.COMPROMISE)]),
        FakeHealthChecker(True),
        FakeTransactionProbe(True),
    )
    incident = s.pipeline.run_once()

    assert incident.status is IncidentStatus.RESOLVED
    assert s.rotator.rotated == ["db_password"]
    assert s.restarter.restarted == []


def test_not_resolved_while_transaction_fails():
    s = Setup(
        FakeDetector([anomaly(IncidentKind.AVAILABILITY)]),
        FakeHealthChecker(True),
        FakeTransactionProbe(False),
        max_attempts=2,
    )
    incident = s.pipeline.run_once()

    assert incident.status is IncidentStatus.FAILED
    assert s.publisher.names[-1] == "incident.failed"
    assert s.restarter.restarted == ["api", "api"]  # 2 tentatives


def test_second_attempt_can_recover():
    s = Setup(
        FakeDetector([anomaly(IncidentKind.AVAILABILITY)]),
        FakeHealthChecker(False, True),
        FakeTransactionProbe(True),
    )
    incident = s.pipeline.run_once()

    assert incident.status is IncidentStatus.RESOLVED
    resolved = [e for e in s.publisher.events if e.event == "incident.resolved"][0]
    assert resolved.data["attempts"] == 2


def test_failing_action_does_not_stop_the_others():
    class BoomAction:
        name = "boom"

        def execute(self, incident: Incident) -> ActionResult:
            raise RuntimeError("proxy docker indisponible")

    restarter = FakeContainerRestarter()
    publisher = InMemoryPublisher()
    pipeline = RemediationPipeline(
        FakeDetector([anomaly(IncidentKind.AVAILABILITY)]),
        KindBasedPolicy(
            {IncidentKind.AVAILABILITY: [BoomAction(), RestartServiceAction(restarter)]}
        ),
        HealthAndProbeVerifier(FakeHealthChecker(True), FakeTransactionProbe(True)),
        publisher,
    )
    incident = pipeline.run_once()

    assert restarter.restarted == ["api"]
    assert incident.status is IncidentStatus.RESOLVED
    failed = [e for e in publisher.events if e.event == "action.executed" and not e.data["success"]]
    assert len(failed) == 1


def test_all_events_share_the_incident_trace_id():
    s = Setup(
        FakeDetector([anomaly(IncidentKind.AVAILABILITY)]),
        FakeHealthChecker(True),
        FakeTransactionProbe(True),
    )
    incident = s.pipeline.run_once()
    assert {e.trace_id for e in s.publisher.events} == {incident.trace_id}
    assert {e.service for e in s.publisher.events} == {"remediation"}
