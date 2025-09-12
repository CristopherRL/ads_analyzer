# === File: src/tools/facebook_tools.py ===

import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from langchain.tools import BaseTool
from langchain.schema import BaseMessage
from pydantic import BaseModel, Field

from src.database import get_db
from src.models import FacebookAccount, ApiCache
from src.facebook_api import get_campaign_data_for_period
from config import CACHE_EXPIRATION_HOURS
from src.logging_config import get_logger

logger = get_logger(__name__)

# === Input Schemas for Tools ===

class ListClientsInput(BaseModel):
    """Input schema for list_available_clients_tool."""
    user_id: str = Field(..., description="User identifier (e.g., email)")

class FacebookAnalysisInput(BaseModel):
    """Input schema for facebook_ads_analysis_tool."""
    ad_account_id: str = Field(..., description="Facebook Ad Account ID (e.g., act_123456)")
    campaign_type: str = Field(default="lead_form", description="Type of campaigns to analyze: 'lead_form', 'traffic', 'conversion'")

# === Helper Functions ===

def _calculate_date_ranges() -> tuple:
    """
    Calculate date ranges for last month and previous month.
    
    Returns:
        tuple: (last_month_start, last_month_end, prev_month_start, prev_month_end)
    """
    today = datetime.today().date()
    last_month_end = today.replace(day=1) - relativedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    prev_month_end = last_month_start - relativedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    
    return last_month_start, last_month_end, prev_month_start, prev_month_end

def _filter_campaigns_by_type(campaigns_data: List[Dict], campaign_type: str = "lead_form") -> List[Dict]:
    """
    Filter campaigns by type with future extensibility.
    
    Args:
        campaigns_data: Raw campaign data from Facebook API
        campaign_type: Type of campaigns to filter ("lead_form", "traffic", "conversion")
    
    Returns:
        Filtered list with only specified campaign type
    """
    if campaign_type == "lead_form":
        # Current implementation - filter for "lead form" campaigns
        filtered_data = [campaign for campaign in campaigns_data 
                        if 'lead form' in campaign.get('name', '').lower()]
        logger.info(f"Filtered {len(filtered_data)} lead form campaigns from {len(campaigns_data)} total campaigns")
    
    elif campaign_type == "traffic":
        # TODO: Implement traffic campaign filtering
        # Filter for campaigns with 'trafico' or 'traffic' in name
        logger.info("Traffic campaign filtering not yet implemented")
        filtered_data = []
        pass
    
    elif campaign_type == "conversion":
        # TODO: Implement conversion campaign filtering  
        # Filter for campaigns with 'conversion' in name
        logger.info("Conversion campaign filtering not yet implemented")
        filtered_data = []
        pass
    
    else:
        raise ValueError(f"Unsupported campaign type: {campaign_type}")
    
    return filtered_data

def _get_cached_data(ad_account_id: str, campaign_type: str, start_date: datetime, end_date: datetime, db: Session) -> Optional[Dict]:
    """
    Retrieve cached campaign data if available and not expired.
    
    Args:
        ad_account_id: Facebook Ad Account ID
        campaign_type: Type of campaigns
        start_date: Start date for data
        end_date: End date for data
        db: Database session
    
    Returns:
        Cached data if available and valid, None otherwise
    """
    cache_key = f"campaign_data_{ad_account_id}_{campaign_type}_{start_date}_{end_date}"
    
    try:
        # Check for valid cache entry
        cache_entry = db.query(ApiCache).filter(
            and_(
                ApiCache.ad_account_id == ad_account_id,
                ApiCache.cache_key == cache_key,
                ApiCache.expires_at > datetime.now()
            )
        ).first()
        
        if cache_entry:
            logger.info(f"Using cached data for {cache_key}")
            return cache_entry.data
        else:
            logger.info(f"No valid cache found for {cache_key}")
            return None
            
    except Exception as e:
        logger.error(f"Error retrieving cached data: {e}")
        return None

def _save_to_cache(ad_account_id: str, campaign_type: str, start_date: datetime, end_date: datetime, data: Dict, db: Session) -> bool:
    """
    Save campaign data to cache with expiration.
    
    Args:
        ad_account_id: Facebook Ad Account ID
        campaign_type: Type of campaigns
        start_date: Start date for data
        end_date: End date for data
        data: Data to cache
        db: Database session
    
    Returns:
        True if saved successfully, False otherwise
    """
    cache_key = f"campaign_data_{ad_account_id}_{campaign_type}_{start_date}_{end_date}"
    expires_at = datetime.now() + timedelta(hours=CACHE_EXPIRATION_HOURS)  # Configurable cache expiration
    
    try:
        # Remove any existing cache entries for this key
        db.query(ApiCache).filter(ApiCache.cache_key == cache_key).delete()
        
        # Create new cache entry
        cache_entry = ApiCache(
            ad_account_id=ad_account_id,
            cache_key=cache_key,
            data=data,
            expires_at=expires_at
        )
        
        db.add(cache_entry)
        db.commit()
        
        logger.info(f"Saved data to cache: {cache_key}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving to cache: {e}")
        db.rollback()
        return False

# === LangChain Tools ===

class ListAvailableClientsTool(BaseTool):
    """
    Tool to list available Facebook advertising accounts for a user.
    """
    name = "list_available_clients"
    description = "List all available Facebook advertising accounts for a specific user. Use this to show the user which clients/accounts they can analyze."
    args_schema = ListClientsInput
    
    def _run(self, user_id: str) -> str:
        """
        Execute the tool to list available clients.
        
        Args:
            user_id: User identifier (e.g., email)
        
        Returns:
            String representation of available accounts
        """
        try:
            # Get database session
            db_gen = get_db()
            db = next(db_gen)
            
            # Query Facebook accounts for the user
            accounts = db.query(FacebookAccount).filter(
                FacebookAccount.user_id == user_id
            ).all()
            
            if not accounts:
                return f"No Facebook advertising accounts found for user: {user_id}"
            
            # Format response
            account_list = []
            for account in accounts:
                account_info = {
                    "account_name": account.account_name or "Unnamed Account",
                    "ad_account_id": account.ad_account_id,
                    "created_at": account.created_at.strftime("%Y-%m-%d")
                }
                account_list.append(account_info)
            
            # Create formatted response
            response = f"Available Facebook advertising accounts for {user_id}:\n\n"
            for i, account in enumerate(account_list, 1):
                response += f"{i}. {account['account_name']} (ID: {account['ad_account_id']})\n"
            
            logger.info(f"Listed {len(accounts)} accounts for user {user_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error listing available clients: {e}")
            return f"Error retrieving accounts for user {user_id}: {str(e)}"
        finally:
            if 'db' in locals():
                db.close()

class FacebookAdsAnalysisTool(BaseTool):
    """
    Tool to analyze Facebook advertising campaign data with caching support.
    """
    name = "facebook_ads_analysis"
    description = "Analyze Facebook advertising campaign data for a specific account. Returns performance data for the last two months with caching for efficiency."
    args_schema = FacebookAnalysisInput
    
    def _run(self, ad_account_id: str, campaign_type: str = "lead_form") -> str:
        """
        Execute the tool to analyze Facebook ads data.
        
        Args:
            ad_account_id: Facebook Ad Account ID (e.g., act_123456)
            campaign_type: Type of campaigns to analyze (default: "lead_form")
        
        Returns:
            String representation of analysis results
        """
        try:
            # Get database session
            db_gen = get_db()
            db = next(db_gen)
            
            # Calculate date ranges
            last_month_start, last_month_end, prev_month_start, prev_month_end = _calculate_date_ranges()
            
            logger.info(f"Analyzing {campaign_type} campaigns for {ad_account_id}")
            logger.info(f"Date ranges: Last month ({last_month_start} to {last_month_end}), Previous month ({prev_month_start} to {prev_month_end})")
            
            # Check cache for both periods
            last_month_cached = _get_cached_data(ad_account_id, campaign_type, last_month_start, last_month_end, db)
            prev_month_cached = _get_cached_data(ad_account_id, campaign_type, prev_month_start, prev_month_end, db)
            
            # Get data for last month
            if last_month_cached:
                df_last_month = pd.DataFrame(last_month_cached)
                logger.info("Using cached data for last month")
            else:
                logger.info("Fetching fresh data for last month from Facebook API")
                df_last_month = get_campaign_data_for_period(ad_account_id, last_month_start, last_month_end)
                
                # Filter by campaign type
                if not df_last_month.empty:
                    # Convert DataFrame to list of dicts for filtering
                    campaigns_list = df_last_month.to_dict('records')
                    filtered_campaigns = _filter_campaigns_by_type(campaigns_list, campaign_type)
                    df_last_month = pd.DataFrame(filtered_campaigns) if filtered_campaigns else pd.DataFrame()
                
                # Save to cache
                if not df_last_month.empty:
                    _save_to_cache(ad_account_id, campaign_type, last_month_start, last_month_end, df_last_month.to_dict('records'), db)
            
            # Get data for previous month
            if prev_month_cached:
                df_prev_month = pd.DataFrame(prev_month_cached)
                logger.info("Using cached data for previous month")
            else:
                logger.info("Fetching fresh data for previous month from Facebook API")
                df_prev_month = get_campaign_data_for_period(ad_account_id, prev_month_start, prev_month_end)
                
                # Filter by campaign type
                if not df_prev_month.empty:
                    # Convert DataFrame to list of dicts for filtering
                    campaigns_list = df_prev_month.to_dict('records')
                    filtered_campaigns = _filter_campaigns_by_type(campaigns_list, campaign_type)
                    df_prev_month = pd.DataFrame(filtered_campaigns) if filtered_campaigns else pd.DataFrame()
                
                # Save to cache
                if not df_prev_month.empty:
                    _save_to_cache(ad_account_id, campaign_type, prev_month_start, prev_month_end, df_prev_month.to_dict('records'), db)
            
            # Prepare response
            if df_last_month.empty and df_prev_month.empty:
                return f"No {campaign_type} campaign data found for account {ad_account_id} in the last two months."
            
            # Create summary response
            response = f"Facebook Ads Analysis for {ad_account_id} ({campaign_type} campaigns):\n\n"
            
            if not df_last_month.empty:
                response += f"Last Month ({last_month_start} to {last_month_end}):\n"
                response += f"- {len(df_last_month)} campaigns found\n"
                response += f"- Total spend: ${df_last_month['Importe gastado (CLP)'].sum():.2f} CLP\n"
                response += f"- Total results: {df_last_month['Resultados'].sum()}\n\n"
            
            if not df_prev_month.empty:
                response += f"Previous Month ({prev_month_start} to {prev_month_end}):\n"
                response += f"- {len(df_prev_month)} campaigns found\n"
                response += f"- Total spend: ${df_prev_month['Importe gastado (CLP)'].sum():.2f} CLP\n"
                response += f"- Total results: {df_prev_month['Resultados'].sum()}\n\n"
            
            response += "Data is ready for detailed analysis. The agent can now provide insights and recommendations."
            
            logger.info(f"Analysis completed for {ad_account_id} - {campaign_type} campaigns")
            return response
            
        except Exception as e:
            logger.error(f"Error in Facebook ads analysis: {e}")
            return f"Error analyzing Facebook ads data for {ad_account_id}: {str(e)}"
        finally:
            if 'db' in locals():
                db.close()

# === Tool Instances ===

# Create tool instances for use in the agent
list_available_clients_tool = ListAvailableClientsTool()
facebook_ads_analysis_tool = FacebookAdsAnalysisTool()

# Export tools for use in agent
__all__ = [
    "ListAvailableClientsTool",
    "FacebookAdsAnalysisTool", 
    "list_available_clients_tool",
    "facebook_ads_analysis_tool"
]
