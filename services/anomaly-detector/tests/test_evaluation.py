from app.application.evaluation import count_alarms, evaluate_model
from app.domain.models import MetricSample
from tests.fakes import FLOOD, NORMAL, ThresholdModel


def at_rate(rate: float) -> MetricSample:
    return MetricSample(rate, 0.0, 0.05, 1.0)


def test_alarm_needs_consecutive_anomalies():
    assert count_alarms([True, True, False, True, True], 3) == (0, None)
    assert count_alarms([True, True, True], 3) == (1, 3)


def test_alarm_series_restarts_after_each_alarm():
    assert count_alarms([True] * 7, 3) == (2, 3)


def test_clean_normal_traffic_and_detected_flood():
    report = evaluate_model(
        ThresholdModel(), [NORMAL] * 10, [NORMAL, *([FLOOD] * 5)], confirmations=3
    )
    assert report.false_positive_samples == 0
    assert report.false_alarms == 0
    assert report.false_positive_rate == 0.0
    assert report.attack_detected
    assert report.detection_delay_samples == 4  # 1 mesure normale puis 3 anormales
    assert report.detection_rate == 5 / 6


def test_isolated_spike_is_a_false_positive_sample_but_not_a_false_alarm():
    traffic = [NORMAL, at_rate(500), NORMAL, NORMAL]
    report = evaluate_model(ThresholdModel(), traffic, [], confirmations=3)
    assert report.false_positive_samples == 1
    assert report.false_alarms == 0
    assert report.false_positive_rate == 0.25


def test_missed_attack_is_reported():
    report = evaluate_model(ThresholdModel(), [NORMAL], [NORMAL] * 4, confirmations=3)
    assert not report.attack_detected
    assert report.detection_delay_samples is None
    assert report.detection_rate == 0.0
