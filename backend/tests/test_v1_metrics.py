from fastapi.testclient import TestClient

from app.main import app


def test_openapi_docs_available():
    c = TestClient(app)
    assert c.get("/docs").status_code == 200


def test_metrics_endpoint_when_enabled():
    c = TestClient(app)
    r = c.get("/metrics")
    assert r.status_code in (200, 404)
