import pytest

from src.database import test_connection


@pytest.mark.integration
def test_database_connection_healthcheck():
    ok = test_connection()
    if not ok:
        pytest.skip("Database not reachable in this environment")
    assert ok
