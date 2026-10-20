import httpx
import pytest

from app.adapters.loki_locator import LokiAttackerLocator


def locator(rows: list[tuple[str, float]], **kwargs) -> LokiAttackerLocator:
    body = {"data": {"result": [{"metric": {"sub": s}, "value": [0, str(n)]} for s, n in rows]}}
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
    return LokiAttackerLocator(client, "http://loki:3100", **kwargs)


def test_designe_le_compte_dominant():
    assert locator([("attaquant", 900), ("alice", 20)]).locate() == "attaquant"


def test_ne_designe_personne_sans_volume_suffisant():
    assert locator([("alice", 30), ("bob", 5)]).locate() is None


def test_ne_designe_personne_si_le_trafic_est_reparti():
    rows = [("a", 150), ("b", 140), ("c", 130)]
    assert locator(rows).locate() is None


def test_aucune_requete_authentifiee():
    assert locator([]).locate() is None


def test_interroge_les_logs_du_waf_par_compte():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["query"] = request.url.params["query"]
        seen["url"] = request.url.path
        return httpx.Response(200, json={"data": {"result": []}})

    LokiAttackerLocator(
        httpx.Client(transport=httpx.MockTransport(handler)), "http://loki:3100"
    ).locate()
    assert seen["url"] == "/loki/api/v1/query"
    assert 'service="waf"' in seen["query"]
    assert "sum by (sub)" in seen["query"]


def test_loki_en_erreur_leve():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    with pytest.raises(httpx.HTTPStatusError):
        LokiAttackerLocator(client, "http://loki:3100").locate()
