from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.security import hash_refresh_token, new_refresh_token_plain_and_hash


def test_refresh_missing_token_validation():
    c = TestClient(app)
    r = c.post("/auth/refresh", json={})
    assert r.status_code == 422


def test_logout_without_auth():
    c = TestClient(app)
    r = c.post("/auth/logout", json={})
    assert r.status_code == 401


def test_login_rate_limit_eventually_429(monkeypatch):
    monkeypatch.setattr(settings, "login_rate_per_minute", 10)
    c = TestClient(app)
    for _ in range(10):
        r = c.post(
            "/auth/login",
            json={"email": "definitely-not-in-db@example.com", "password": "x"},
        )
        assert r.status_code == 401
    last = c.post(
        "/auth/login",
        json={"email": "definitely-not-in-db@example.com", "password": "x"},
    )
    assert last.status_code == 429


def test_refresh_token_hash_is_stable():
    assert hash_refresh_token("hello") == hash_refresh_token("hello")
    a, h = new_refresh_token_plain_and_hash()
    assert len(a) > 20
    assert len(h) == 64
