import httpx
from fastapi.testclient import TestClient

from app.adapters.isolation_forest import IsolationForestTrainer, JoblibModelStore
from app.config import Settings
from app.main import create_app
from tests.test_isolation_forest import normal_samples


def test_app_demarre_expose_health_et_metrics(tmp_path):
    JoblibModelStore(tmp_path / "m.joblib").save(IsolationForestTrainer().fit(normal_samples()))
    settings = Settings(
        prometheus_url="http://prom",
        remediation_url="http://rem",
        ingest_token="t",
        model_path=tmp_path / "m.joblib",
        dataset_path=tmp_path / "d.csv",
        poll_interval_s=3600,
    )
    empty = httpx.MockTransport(lambda r: httpx.Response(200, json={"data": {"result": []}}))
    with TestClient(create_app(settings, httpx.Client(transport=empty))) as http:
        assert http.get("/health").json() == {"status": "ok"}
        assert "anomaly_score" in http.get("/metrics").text
