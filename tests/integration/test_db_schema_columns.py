import pytest
from sqlalchemy import inspect

from src.database import engine, check_connection


EXPECTED_COLUMNS = {
    'users': ['id', 'email', 'name', 'password', 'is_active', 'created_at', 'updated_at'],
    'facebook_accounts': ['id', 'ad_account_id', 'account_name', 'key_vault_secret_name', 'created_at'],
    'user_facebook_accounts': ['id', 'user_id', 'facebook_account_id', 'assigned_at', 'assigned_by', 'is_active', 'notes'],
    'api_cache': ['id', 'ad_account_id', 'date_period', 'query_hash', 'result_json', 'created_at'],
    'conversation_history': ['id', 'session_id', 'user_id', 'user_prompt', 'full_prompt_sent', 'llm_response', 'llm_params', 'tokens_used', 'estimated_cost_usd', 'timestamp'],
    'prompt_versions': ['id', 'prompt_name', 'version', 'prompt_text', 'is_active', 'created_at'],
    'campaign_performance_data': ['id', 'ad_account_id', 'campaign_id', 'campaign_name', 'date', 'metrics', 'facebook_account_id', 'created_at'],
    'model_pricing': ['id', 'model_name', 'input_cost_per_1k_tokens', 'output_cost_per_1k_tokens', 'effective_date', 'created_at', 'updated_at'],
    'analysis_results': ['id', 'user_id', 'session_id', 'analysis_type', 'facebook_account_id', 'result_text', 'analysis_metadata', 'created_at'],
}


@pytest.mark.integration
def test_tables_exist_and_columns_match():
    if not check_connection():
        pytest.skip("Database not reachable in this environment")

    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())

    missing_tables = [t for t in EXPECTED_COLUMNS if t not in existing_tables]
    assert not missing_tables, f"Missing tables: {missing_tables}"

    for table_name, expected_cols in EXPECTED_COLUMNS.items():
        cols = [c['name'] for c in insp.get_columns(table_name)]
        missing_cols = sorted(set(expected_cols) - set(cols))
        extra_cols = sorted(set(cols) - set(expected_cols))
        assert not missing_cols, f"{table_name} missing columns: {missing_cols}"
        assert not extra_cols, f"{table_name} extra columns: {extra_cols}"
