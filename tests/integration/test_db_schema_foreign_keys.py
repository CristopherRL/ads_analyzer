import pytest
from sqlalchemy import text

from src.database import engine, SessionLocal, test_connection


EXPECTED_FKS = {
    ('user_facebook_accounts', 'user_id', 'users', 'id'),
    ('user_facebook_accounts', 'facebook_account_id', 'facebook_accounts', 'id'),
    ('conversation_history', 'user_id', 'users', 'id'),
    ('analysis_results', 'user_id', 'users', 'id'),
    ('analysis_results', 'facebook_account_id', 'facebook_accounts', 'id'),
    ('campaign_performance_data', 'facebook_account_id', 'facebook_accounts', 'id'),
}


@pytest.mark.integration
def test_expected_foreign_keys_exist_postgres():
    if not test_connection():
        pytest.skip("Database not reachable in this environment")
    if engine.dialect.name != 'postgresql':
        pytest.skip("FK check uses information_schema; skipping for non-PostgreSQL")

    db = SessionLocal()
    try:
        result = db.execute(text(
            """
            SELECT 
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.column_name
            """
        ))
        existing = {(r.table_name, r.column_name, r.foreign_table_name, r.foreign_column_name) for r in result.fetchall()}
        missing = sorted(EXPECTED_FKS - existing)
        assert not missing, f"Missing foreign keys: {missing}"
    finally:
        db.close()
