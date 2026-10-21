import io

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_manager_can_list_direct_report_documents(client):
    rita = client.post("/auth/login", json={"email": "rita.gomez@company.com", "password": "rita@123"})
    jamal = client.post("/auth/login", json={"email": "jamal.mitchell@company.com", "password": "jamal@123"})
    if rita.status_code != 200 or jamal.status_code != 200:
        pytest.skip("Seeded rita/jamal not available")
    jamal_id = jamal.json()["user"]["id"]
    token = rita.json()["access_token"]
    r = client.get(
        f"/employees/{jamal_id}/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert "items" in r.json()


def test_manager_forbidden_documents_outside_team(client):
    rita = client.post("/auth/login", json={"email": "rita.gomez@company.com", "password": "rita@123"})
    maya = client.post("/auth/login", json={"email": "maya.chen@company.com", "password": "maya@123"})
    if rita.status_code != 200 or maya.status_code != 200:
        pytest.skip("Seeded rita/maya not available")
    maya_id = maya.json()["user"]["id"]
    token = rita.json()["access_token"]
    r = client.get(
        f"/employees/{maya_id}/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_upload_then_download_audit_roundtrip(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.upload_dir", str(tmp_path))
    john = client.post("/auth/login", json={"email": "john.doe@company.com", "password": "admin@123"})
    if john.status_code != 200:
        pytest.skip("Seeded admin not available")
    uid = john.json()["user"]["id"]
    token = john.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("note.txt", io.BytesIO(b"hello hrms"), "text/plain")}
    data = {"label": "pytest-note"}
    up = client.post(f"/employees/{uid}/documents", headers=headers, data=data, files=files)
    assert up.status_code == 200
    doc_id = up.json()["id"]

    dl = client.get(
        f"/employees/{uid}/documents/{doc_id}/file",
        headers=headers,
    )
    assert dl.status_code == 200
    assert b"hello hrms" in dl.content

    adm = client.post("/auth/login", json={"email": "john.doe@company.com", "password": "admin@123"})
    adm_token = adm.json()["access_token"]
    aud = client.get(
        "/audit-events?limit=20&action_prefix=document.",
        headers={"Authorization": f"Bearer {adm_token}"},
    )
    assert aud.status_code == 200
    actions = {x["action"] for x in aud.json().get("items", [])}
    assert "document.upload" in actions
    assert "document.download" in actions

    rm = client.delete(
        f"/employees/{uid}/documents/{doc_id}",
        headers=headers,
    )
    assert rm.status_code == 204
