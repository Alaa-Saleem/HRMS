import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_audit_events_forbidden_for_employee():
    c = TestClient(app)
    emp_login = c.post(
        "/auth/login",
        json={"email": "maya.chen@company.com", "password": "maya@123"},
    )
    if emp_login.status_code != 200:
        pytest.skip("Seeded employee maya.chen not available")

    token = emp_login.json()["access_token"]
    r = c.get("/audit-events", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_audit_events_admin_ok():
    c = TestClient(app)
    login = c.post(
        "/auth/login",
        json={"email": "john.doe@company.com", "password": "admin@123"},
    )
    if login.status_code != 200:
        pytest.skip("Seeded admin not available")
    token = login.json()["access_token"]
    r = c.get("/audit-events?limit=5", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "total" in body
    assert isinstance(body["items"], list)
