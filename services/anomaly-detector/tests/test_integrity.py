from app.application.integrity import IntegrityWatchService
from app.domain.models import IncidentKind, IntegritySnapshot
from tests.fakes import FakeClock, RecordingReporter


class ScriptedIntegrity:
    def __init__(self, items):
        self._items = list(items)

    def snapshot(self):
        item = self._items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def snap(transactions=4, ledger=8, unbalanced=0):
    return IntegritySnapshot(transactions, ledger, unbalanced)


def build(items, reporter=None, clock=None, cooldown_s=90.0):
    reporter = reporter or RecordingReporter()
    clock = clock or FakeClock()
    service = IntegrityWatchService(
        ScriptedIntegrity(items),
        reporter,
        target_service="api",
        cooldown_s=cooldown_s,
        clock=clock,
    )
    return service, reporter, clock


def test_croissance_normale_ne_signale_rien():
    service, reporter, _ = build([snap(4, 8), snap(5, 10), snap(5, 10)])
    assert [service.tick() for _ in range(3)] == [None] * 3
    assert reporter.detections == []


def test_suppression_de_donnees_est_signalee():
    service, reporter, _ = build([snap(4, 8), snap(0, 0)])
    assert service.tick() is None
    detection = service.tick()
    assert detection is not None
    assert detection.kind is IncidentKind.DATABASE_CORRUPTION
    assert detection.source == "db-recovery:integrity"
    assert detection.target_service == "api"
    assert reporter.detections == [detection]


def test_ecriture_perdue_seule_est_signalee():
    service, _, _ = build([snap(4, 8), snap(4, 7)])
    service.tick()
    assert service.tick() is not None


def test_transaction_desequilibree_est_signalee_des_la_premiere_mesure():
    service, _, _ = build([snap(4, 8, unbalanced=1)])
    assert service.tick() is not None


def test_apres_restauration_la_reference_est_reapprise():
    service, reporter, clock = build([snap(4, 8), snap(0, 0), snap(2, 4), snap(2, 4)])
    service.tick()
    assert service.tick() is not None
    clock.now = 100.0
    assert service.tick() is None  # compteurs plus bas qu'avant, mais légitimes
    assert service.tick() is None
    assert len(reporter.detections) == 1


def test_delai_de_grace_evite_de_resignaler():
    service, _, clock = build([snap(4, 8), snap(0, 0), snap(4, 8, 1), snap(4, 8, 1)])
    service.tick()
    service.tick()
    clock.now = 10.0
    assert service.tick() is None  # encore corrompu, mais moteur en cours de reprise
    clock.now = 100.0
    assert service.tick() is not None


def test_source_injoignable_ne_signale_pas():
    service, reporter, _ = build([snap(4, 8), ConnectionError("db-recovery"), snap(4, 8)])
    assert [service.tick() for _ in range(3)] == [None] * 3
    assert reporter.detections == []


def test_echec_du_signalement_est_retente():
    reporter = RecordingReporter(fail=True)
    service, _, _ = build([snap(4, 8), snap(0, 0), snap(0, 0)], reporter=reporter)
    service.tick()
    assert service.tick() is None
    reporter.fail = False
    assert service.tick() is not None
