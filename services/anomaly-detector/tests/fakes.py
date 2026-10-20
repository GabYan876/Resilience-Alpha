"""Doublures des ports : substituables aux adaptateurs réels (Liskov)."""

from __future__ import annotations

from app.domain.models import Detection, MetricSample, Verdict

NORMAL = MetricSample(request_rate=20.0, error_ratio=0.0, latency_p95_s=0.05, up=1.0)
FLOOD = MetricSample(request_rate=900.0, error_ratio=0.3, latency_p95_s=2.0, up=1.0)


class ScriptedSource:
    """Rejoue une liste d'échantillons ; une exception de la liste est levée."""

    def __init__(self, items: list[MetricSample | Exception]) -> None:
        self._items = list(items)

    def sample(self) -> MetricSample:
        item = self._items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class ThresholdModel:
    """Anormal dès que le débit dépasse 100 req/s (suffit à piloter le cas d'usage)."""

    def evaluate(self, sample: MetricSample) -> Verdict:
        return Verdict(score=sample.request_rate / 1000, anomalous=sample.request_rate > 100)


class RecordingReporter:
    def __init__(self, fail: bool = False) -> None:
        self.detections: list[Detection] = []
        self.fail = fail

    def report(self, detection: Detection) -> None:
        if self.fail:
            raise ConnectionError("moteur injoignable")
        self.detections.append(detection)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now
