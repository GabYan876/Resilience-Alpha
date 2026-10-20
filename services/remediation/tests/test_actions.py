from app.application.actions import (
    BlockIpAction,
    BlockSubjectAction,
    RestartServiceAction,
    RestoreDatabaseAction,
    RotateSecretAction,
    ScaleServiceAction,
)
from app.domain.models import Anomaly, Incident, IncidentKind
from tests.fakes import (
    FakeContainerRestarter,
    FakeDatabaseRestorer,
    FakeIpBlocker,
    FakeSecretRotator,
    FakeServiceScaler,
    FakeSubjectBlocker,
)


def make_incident(ip: str | None = "192.168.137.50") -> Incident:
    return Incident(
        Anomaly(score=0.9, source="test", kind_hint=IncidentKind.AVAILABILITY, attacker_ip=ip)
    )


def test_block_ip_blocks_attacker():
    blocker = FakeIpBlocker()
    result = BlockIpAction(blocker).execute(make_incident())
    assert result.success
    assert blocker.blocked == {"192.168.137.50"}


def test_block_ip_fails_without_ip():
    blocker = FakeIpBlocker()
    result = BlockIpAction(blocker).execute(make_incident(ip=None))
    assert not result.success
    assert blocker.blocked == set()


def test_restart_targets_incident_service():
    restarter = FakeContainerRestarter()
    assert RestartServiceAction(restarter).execute(make_incident()).success
    assert restarter.restarted == ["api"]


def test_restore_database_uses_latest_backup_and_is_required():
    restorer = FakeDatabaseRestorer()
    result = RestoreDatabaseAction(restorer).execute(make_incident())
    assert result.success and result.required
    assert result.detail == "restauration=derniere_sauvegarde"
    assert restorer.restores == 1


def test_scale_uses_configured_replicas():
    scaler = FakeServiceScaler()
    ScaleServiceAction(scaler, replicas=3).execute(make_incident())
    assert scaler.scaled == [("api", 3)]


def test_rotate_secret_never_leaks_value():
    rotator = FakeSecretRotator()
    result = RotateSecretAction(rotator, "db_password").execute(make_incident())
    assert rotator.rotated == ["db_password"]
    assert result.detail == "secret=db_password"


def test_block_subject_blocks_attacker_account():
    blocker = FakeSubjectBlocker()
    incident = Incident(
        Anomaly(
            score=0.9, source="test", kind_hint=IncidentKind.AVAILABILITY, attacker_subject="u-1"
        )
    )
    assert BlockSubjectAction(blocker).execute(incident).success
    assert blocker.blocked == {"u-1"}


def test_block_subject_fails_without_subject():
    blocker = FakeSubjectBlocker()
    assert not BlockSubjectAction(blocker).execute(make_incident()).success
    assert blocker.blocked == set()
