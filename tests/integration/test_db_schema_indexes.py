import pytest
from sqlalchemy import text

from src.database import engine, SessionLocal, check_connection


EXPECTED_INDEXES = [
    'idx_users_email', 'idx_users_active',
    'idx_facebook_accounts_ad_account_id',
    'idx_user_facebook_accounts_user_id', 'idx_user_facebook_accounts_facebook_id',
    'idx_api_cache_account_period', 'idx_api_cache_hash',
    'idx_conversation_user_session', 'idx_conversation_timestamp',
    'idx_prompt_name_version', 'idx_prompt_active',
    'idx_campaign_account_date', 'idx_campaign_id_date',
    'idx_model_pricing_model_date',
    'idx_analysis_results_user_id', 'idx_analysis_results_type',
]


@pytest.mark.integration
def test_expected_indexes_exist_postgres():
    if not check_connection():
        pytest.skip("Database not reachable in this environment")
    if engine.dialect.name != 'postgresql':
        pytest.skip("Index check uses pg_indexes; skipping for non-PostgreSQL")

    db = SessionLocal()
    try:
        result = db.execute(text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY indexname
            """
        ))
        existing_index_names = {row.indexname for row in result.fetchall()}
        missing = sorted(set(EXPECTED_INDEXES) - existing_index_names)
        assert not missing, f"Missing indexes: {missing}"
    finally:
        db.close()
