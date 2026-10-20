import httpx

from app.adapters.prometheus_source import PrometheusMetricsSource


def source_with(responses: dict[str, str | None]) -> PrometheusMetricsSource:
    """`responses` : fragment de requête -> valeur (None = aucune série, "NaN" possible).

    Le premier fragment contenu dans la requête gagne : mettre le plus spécifique en tête.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        query = request.url.params["query"]
        value = responses[next(k for k in responses if k in query)]
        result = [] if value is None else [{"metric": {}, "value": [0, value]}]
        return httpx.Response(200, json={"status": "success", "data": {"result": result}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return PrometheusMetricsSource(client, "http://prom", "api")


def test_lit_les_quatre_mesures():
    sample = source_with(
        {"5.*": "0.1", "bucket": "0.25", "up{": "1", "rate(http_requests_total": "42"}
    ).sample()
    assert sample.as_vector() == [42.0, 0.1, 0.25, 1.0]


def test_serie_absente_et_nan_valent_zero():
    sample = source_with(
        {"5.*": "NaN", "bucket": None, "up{": None, "rate(http_requests_total": None}
    ).sample()
    assert sample.as_vector() == [0.0, 0.0, 0.0, 0.0]


def test_filtre_sur_le_service_demande():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params["query"])
        return httpx.Response(200, json={"data": {"result": []}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    PrometheusMetricsSource(client, "http://p", "auth").sample()
    assert len(seen) == 4
    assert all('service="auth"' in q for q in seen)
