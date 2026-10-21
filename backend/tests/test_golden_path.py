"""Full-stack smoke tests against a seeded Postgres database.

Run locally after `alembic upgrade head` and `python scripts/seed.py`.
CI runs migrations + seed before pytest.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _login(email: str, password: str) -> tuple[TestClient, str] | None:
    c = TestClient(app)
    r = c.post("/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        return None
    return c, r.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def seeded_db():
    pair = _login("john.doe@company.com", "admin@123")
    if pair is None:
        pytest.skip("Seeded admin login failed; run alembic upgrade head && python scripts/seed.py")
    return pair


def test_workspace_requires_auth():
    c = TestClient(app)
    assert c.get("/workspace").status_code == 401


def test_workspace_200_for_admin(seeded_db):
    c, token = seeded_db
    r = c.get("/workspace", headers=_auth_headers(token))
    assert r.status_code == 200
    body = r.json()
    assert "employees" in body
    assert len(body["employees"]) >= 1


def test_refresh_roundtrip(seeded_db):
    c, _ = seeded_db
    login = c.post(
        "/auth/login",
        json={"email": "john.doe@company.com", "password": "admin@123"},
    )
    assert login.status_code == 200
    refresh = login.json()["refresh_token"]
    r2 = c.post("/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_employees_list_paginated(seeded_db):
    c, token = seeded_db
    r = c.get("/employees?limit=3&offset=0", headers=_auth_headers(token))
    assert r.status_code == 200
    data = r.json()
    assert "items" in data and "total" in data
    assert len(data["items"]) <= 3


def test_leave_create_and_manager_approval(seeded_db):
    c, _ = seeded_db
    liam = _login("liam.watkins@company.com", "liam@123")
    rita = _login("rita.gomez@company.com", "rita@123")
    if liam is None or rita is None:
        pytest.skip("Seeded employees missing")

    lc, liam_tok = liam
    create = lc.post(
        "/leave-requests",
        headers=_auth_headers(liam_tok),
        json={
            "type": "Annual",
            "start": "2030-12-01",
            "end": "2030-12-03",
            "reason": "pytest",
        },
    )
    assert create.status_code == 201
    leave_id = create.json()["id"]

    rc, rita_tok = rita
    decision = rc.patch(
        f"/leave-requests/{leave_id}/status",
        headers=_auth_headers(rita_tok),
        json={"status": "approved"},
    )
    assert decision.status_code == 200
    assert decision.json().get("status") == "approved"
