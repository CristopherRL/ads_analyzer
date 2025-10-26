import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.tools.facebook_tools import ListAvailableClientsTool, FacebookAdsAnalysisTool

@pytest.fixture
def mock_db_session():
    """Fixture to create a mock database session."""
    db_session = MagicMock()
    db_session.query.return_value = MagicMock()
    return db_session

@pytest.fixture
def mock_get_db(mock_db_session):
    """Fixture to patch get_db to return the mock_db_session repeatedly."""
    with patch('src.tools.facebook_tools.get_db') as mock_get_db:
        mock_get_db.side_effect = lambda: iter([mock_db_session])
        yield mock_get_db

def test_list_available_clients_tool(mock_db_session, mock_get_db):
    """Test the ListAvailableClientsTool."""
    mock_account = MagicMock()
    mock_account.account_name = "Test Account"
    mock_account.ad_account_id = "act_12345"
    mock_account.created_at.strftime.return_value = "2023-01-01"
    mock_db_session.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_account]

    tool = ListAvailableClientsTool()
    result = tool._run(user_id=1)
    assert "Test Account" in result
    assert "act_12345" in result

@patch('src.tools.facebook_tools._get_cached_data')
@patch('src.tools.facebook_tools.get_campaign_data_for_period')
def test_facebook_ads_analysis_tool_no_cache(mock_get_campaign_data, mock_get_cached_data, mock_get_db):
    """Test the FacebookAdsAnalysisTool when no cache is available."""
    mock_get_cached_data.return_value = None
    df = pd.DataFrame([
        {'Nombre de la campaña': 'Test Lead Form', 'Importe gastado (CLP)': 100.0, 'Resultados': 10},
    ])
    mock_get_campaign_data.return_value = df
    tool = FacebookAdsAnalysisTool()
    result = tool._run(ad_account_id="act_12345")
    assert "Facebook Ads Analysis" in result
    assert "Total spend: $100.00" in result
    assert "Total results: 10" in result
    assert mock_get_campaign_data.call_count == 2

@patch('src.tools.facebook_tools._get_cached_data')
@patch('src.tools.facebook_tools.get_campaign_data_for_period')
def test_facebook_ads_analysis_tool_with_cache(mock_get_campaign_data, mock_get_cached_data, mock_get_db):
    """Test the FacebookAdsAnalysisTool when cache is available."""
    mock_get_cached_data.return_value = [
        {"Nombre de la campaña": "Test Lead Form", "Importe gastado (CLP)": 100.0, "Resultados": 10}
    ]
    tool = FacebookAdsAnalysisTool()
    result = tool._run(ad_account_id="act_12345")
    assert "Facebook Ads Analysis" in result
    assert "Total spend: $100.00" in result
    assert "Total results: 10" in result
    mock_get_campaign_data.assert_not_called()
