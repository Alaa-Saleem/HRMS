from fastapi.testclient import TestClient

from app.main import app


def test_root_returns_service_json():
    c = TestClient(app)
    r = c.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("service") == "HRMS API"
    assert body.get("v1_prefix") == "/v1"
