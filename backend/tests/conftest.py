import pytest

from app.login_rate import reset_login_rate_state


@pytest.fixture(autouse=True)
def _clear_login_rate_between_tests():
    reset_login_rate_state()
    yield
    reset_login_rate_state()
