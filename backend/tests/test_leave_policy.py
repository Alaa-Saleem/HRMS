import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Department, LeaveAccrualLedger, LeavePolicy, LeaveRequest


@pytest.fixture
def client():
    return TestClient(app)


def test_department_leave_policy_denies_wrong_type(client):
    db = SessionLocal()
    dept_id = None
    policy_id = None
    try:
        eng = db.query(Department).filter(Department.code == "ENG").first()
        if not eng:
            pytest.skip("Engineering department (ENG) not seeded")
        dept_id = eng.id
        pol = LeavePolicy(
            name="pytest Sick-only ENG",
            department_id=dept_id,
            rules={
                "allowed_leave_types": ["Sick Leave"],
                "max_consecutive_calendar_days": 14,
                "enforce_ledger": False,
                "hours_per_day": 8,
            },
        )
        db.add(pol)
        db.commit()
        db.refresh(pol)
        policy_id = pol.id

        login = client.post(
            "/auth/login",
            json={"email": "liam.watkins@company.com", "password": "liam@123"},
        )
        if login.status_code != 200:
            pytest.skip("Seeded liam not available")
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        bad = client.post(
            "/leave-requests",
            headers=headers,
            json={
                "type": "Paid Leave",
                "start": "2031-06-01",
                "end": "2031-06-02",
                "reason": "pytest",
            },
        )
        assert bad.status_code == 400

        ok = client.post(
            "/leave-requests",
            headers=headers,
            json={
                "type": "Sick Leave",
                "start": "2031-07-01",
                "end": "2031-07-02",
                "reason": "pytest",
            },
        )
        assert ok.status_code == 201
        leave_id = ok.json()["id"]

        db.delete(db.get(LeaveRequest, leave_id))
        db.commit()
    finally:
        db = SessionLocal()
        try:
            if policy_id:
                db.query(LeavePolicy).filter(LeavePolicy.id == policy_id).delete()
                db.commit()
        finally:
            db.close()


def test_approve_writes_ledger_when_enforced(client):
    db = SessionLocal()
    pol_id = None
    leave_id = None
    try:
        eng = db.query(Department).filter(Department.code == "ENG").first()
        if not eng:
            pytest.skip("Engineering department not seeded")
        pol = LeavePolicy(
            name="pytest ledger ENG",
            department_id=eng.id,
            rules={
                "allowed_leave_types": ["Annual"],
                "max_consecutive_calendar_days": 14,
                "enforce_ledger": True,
                "hours_per_day": 8,
            },
        )
        db.add(pol)
        db.flush()

        login_liam = client.post(
            "/auth/login",
            json={"email": "liam.watkins@company.com", "password": "liam@123"},
        )
        login_rita = client.post(
            "/auth/login",
            json={"email": "rita.gomez@company.com", "password": "rita@123"},
        )
        if login_liam.status_code != 200 or login_rita.status_code != 200:
            pytest.skip("Seeded liam/rita not available")
        liam = login_liam.json()["user"]
        liam_id = liam["id"]

        db.add(
            LeaveAccrualLedger(
                employee_id=liam_id,
                leave_type="Annual",
                hours_delta=40,
                balance_after=40,
                note="pytest seed",
            )
        )
        db.commit()
        db.refresh(pol)
        pol_id = pol.id

        token_liam = login_liam.json()["access_token"]
        create = client.post(
            "/leave-requests",
            headers={"Authorization": f"Bearer {token_liam}"},
            json={
                "type": "Annual",
                "start": "2032-01-10",
                "end": "2032-01-11",
                "reason": "pytest",
            },
        )
        assert create.status_code == 201
        leave_id = create.json()["id"]

        token_rita = login_rita.json()["access_token"]
        patch = client.patch(
            f"/leave-requests/{leave_id}/status",
            headers={"Authorization": f"Bearer {token_rita}"},
            json={"status": "approved"},
        )
        assert patch.status_code == 200

        row = (
            db.query(LeaveAccrualLedger)
            .filter(LeaveAccrualLedger.note != "pytest seed")
            .filter(LeaveAccrualLedger.employee_id == liam_id)
            .order_by(LeaveAccrualLedger.id.desc())
            .first()
        )
        assert row is not None
        assert row.hours_delta < 0
        assert row.balance_after is not None
    finally:
        db = SessionLocal()
        try:
            if leave_id:
                lr = db.get(LeaveRequest, leave_id)
                if lr:
                    db.delete(lr)
            db.query(LeaveAccrualLedger).filter(LeaveAccrualLedger.note == "pytest seed").delete()
            db.query(LeaveAccrualLedger).filter(LeaveAccrualLedger.note.like("%leave approved%")).delete()
            if pol_id:
                db.query(LeavePolicy).filter(LeavePolicy.id == pol_id).delete()
            db.commit()
        finally:
            db.close()
