"""Password reset / invite flows (requires seeded employee + migration)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import Employee, EmployeeCredential
from app.password_reset import issue_password_token
from app.security import hash_password, verify_password


@pytest.fixture
def client():
    return TestClient(app)


def test_forgot_password_503_when_smtp_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "")
    r = client.post("/auth/forgot-password", json={"email": "john.doe@company.com"})
    assert r.status_code == 503


def test_reset_password_updates_credential_and_login(client, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.test")
    monkeypatch.setattr("app.mail_smtp.send_plain_email", lambda *a, **k: None)

    emp_id = None
    db = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.email == "john.doe@company.com").first()
        if not emp:
            pytest.skip("Seeded admin john.doe@company.com not in DB")
        emp_id = emp.id
        plain = issue_password_token(db, employee_id=emp_id, purpose="reset")
        db.commit()
    finally:
        db.close()

    new_pw = "ResetTestPwd99!"
    r = client.post("/auth/reset-password", json={"token": plain, "new_password": new_pw})
    assert r.status_code == 200

    db = SessionLocal()
    try:
        cred = db.get(EmployeeCredential, emp_id)
        assert cred and verify_password(new_pw, cred.password_hash)
    finally:
        db.close()

    login = client.post(
        "/auth/login",
        json={"email": "john.doe@company.com", "password": new_pw},
    )
    assert login.status_code == 200

    db = SessionLocal()
    try:
        cred = db.get(EmployeeCredential, emp_id)
        if cred:
            cred.password_hash = hash_password("admin@123")
            db.commit()
    finally:
        db.close()
