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


def test_le_timeout_du_signalement_depasse_largement_celui_des_requetes_prometheus():
    # Régression : POST /incidents attend la fin du pipeline (décision + action + vérification)
    # côté moteur avant de répondre, bien plus long qu'une requête Prometheus. Un timeout trop
    # court fait croire à un échec alors que le moteur a bien agi, et empêche le délai de grâce
    # de s'enclencher (la détection reste confirmée, donc un nouveau signalement repart au tick
    # suivant) : d'où la rafale d'incidents observée en test réel.
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["timeout"] = request.extensions.get("timeout")
        return httpx.Response(200, json={})

    client = httpx.Client(transport=httpx.MockTransport(handler), timeout=3.0)
    HttpAnomalyReporter(client, "http://remediation:8000", "tok", timeout_s=75.0).report(
        DETECTION
    )
    assert captured["timeout"] == {"connect": 75.0, "read": 75.0, "write": 75.0, "pool": 75.0}
