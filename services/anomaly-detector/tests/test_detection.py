from app.application.detection import DetectionService
from app.domain.models import IncidentKind
from tests.fakes import FLOOD, NORMAL, FakeClock, RecordingReporter, ScriptedSource, ThresholdModel


def build(items, reporter=None, clock=None, confirmations=3, cooldown_s=90.0):
    reporter = reporter or RecordingReporter()
    clock = clock or FakeClock()
    service = DetectionService(
        ScriptedSource(items),
        ThresholdModel(),
        reporter,
        target_service="api",
        confirmations=confirmations,
        cooldown_s=cooldown_s,
        clock=clock,
    )
    return service, reporter, clock


def test_trafic_normal_ne_signale_rien():
    service, reporter, _ = build([NORMAL] * 5)
    assert [service.tick() for _ in range(5)] == [None] * 5
    assert reporter.detections == []


def test_signale_apres_les_confirmations_consecutives():
    service, reporter, _ = build([FLOOD] * 3)
    assert service.tick() is None
    assert service.tick() is None
    detection = service.tick()
    assert detection is not None
    assert detection.kind is IncidentKind.AVAILABILITY
    assert detection.target_service == "api"
    assert detection.source == "prometheus:api"
    assert reporter.detections == [detection]


def test_un_pic_isole_est_ignore():
    service, reporter, _ = build([FLOOD, FLOOD, NORMAL, FLOOD, FLOOD, NORMAL])
    for _ in range(6):
        service.tick()
    assert reporter.detections == []


def test_delai_de_grace_apres_signalement():
    service, reporter, clock = build([FLOOD] * 9, cooldown_s=90.0)
    for _ in range(3):
        service.tick()
    clock.now = 30.0
    for _ in range(3):
        service.tick()
    assert len(reporter.detections) == 1
    clock.now = 100.0
    for _ in range(3):
        service.tick()
    assert len(reporter.detections) == 2


def test_mesure_impossible_ne_leve_pas():
    service, reporter, _ = build([ConnectionError("prometheus"), NORMAL])
    assert service.tick() is None
    assert service.tick() is None
    assert reporter.detections == []


def test_echec_du_signalement_est_retente_a_l_iteration_suivante():
    reporter = RecordingReporter(fail=True)
    service, _, _ = build([FLOOD] * 5, reporter=reporter)
    for _ in range(3):
        assert service.tick() is None
    reporter.fail = False
    assert service.tick() is not None
    assert len(reporter.detections) == 1
