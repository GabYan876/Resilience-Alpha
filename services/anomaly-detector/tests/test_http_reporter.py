import json

import httpx
import pytest

from app.adapters.http_reporter import HttpAnomalyReporter
from app.domain.models import Detection, IncidentKind

DETECTION = Detection(0.7, "prometheus:api", IncidentKind.AVAILABILITY, "api")


def reporter(handler) -> HttpAnomalyReporter:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpAnomalyReporter(client, "http://remediation:8000", "tok")


def test_poste_le_contrat_attendu_par_le_moteur():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={})

    reporter(handler).report(DETECTION)
    assert captured["url"] == "http://remediation:8000/incidents"
    assert captured["auth"] == "Bearer tok"
    assert captured["body"] == {
        "score": 0.7,
        "source": "prometheus:api",
        "kind": "availability",
        "attacker_ip": None,
        "target_service": "api",
    }


def test_refus_du_moteur_leve_une_erreur():
    with pytest.raises(httpx.HTTPStatusError):
        reporter(lambda r: httpx.Response(401)).report(DETECTION)
