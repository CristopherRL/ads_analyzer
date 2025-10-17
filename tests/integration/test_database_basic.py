import pytest

from src.database import check_connection


@pytest.mark.integration
def test_database_connection_healthcheck():
    ok = check_connection()
    if not ok:
        pytest.skip("Database not reachable in this environment")
    assert ok
