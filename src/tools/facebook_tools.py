# === File: src/tools/facebook_tools.py ===

import pandas as pd
import hashlib
import traceback
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign

from langchain.tools import BaseTool
from langchain.schema import BaseMessage
from pydantic import BaseModel, Field

from src.database import get_db
from src.models import FacebookAccount, ApiCache
from config import CACHE_EXPIRATION_HOURS, FB_APP_ID, FB_APP_SECRET, FB_ACCESS_TOKEN
from src.logging_config import get_logger

logger = get_logger(__name__)

# === Facebook API Helper Functions ===

def initialize_facebook_api():
    """Establishes connection with Facebook API."""
    try:
        FacebookAdsApi.init(FB_APP_ID, FB_APP_SECRET, FB_ACCESS_TOKEN)
        logger.info("✅ Facebook API connection successful.")
    except Exception as e:
        logger.error(f"❌ Error initializing Facebook API: {e}")
        raise

def _parse_results(campaign, campaign_insights):
    """
    Private helper function to determine the main result of a campaign,
    based on keywords in the campaign name.
    """
    if not campaign_insights or not campaign_insights[0].get('actions'):
        return 0, 'N/A', 'N/A', 0.0

    insight_data = campaign_insights[0]
    actions = insight_data.get('actions', [])
    cost_per_action = insight_data.get('cost_per_action_type', [])
    campaign_name = campaign.get('name', '').lower()

    # Determine target action based on campaign name
    if 'lead form' in campaign_name:
        target_action = 'offsite_conversion.fb_pixel_custom'
    elif 'conversion' in campaign_name:
        target_action = 'onsite_conversion.lead_grouped'
    elif 'tráfico' in campaign_name or 'trafico' in campaign_name:
        target_action = 'link_click'
    else:
        target_action = 'onsite_conversion.lead_grouped'

    # Find the specific action - if not found, return empty values (campaign will appear with empty values)
    action_obj = next((a for a in actions if a['action_type'] == target_action), None)
    if not action_obj:
        return 0, 'N/A', 'N/A', 0.0

    # Action found - extract values
    result_count = int(action_obj['value'])
    cost_obj = next((c for c in cost_per_action if c['action_type'] == target_action), None)
    cost_per_result = float(cost_obj['value']) if cost_obj else 0.0
    
    return result_count, target_action, target_action, cost_per_result

def get_campaign_data_for_period(ad_account_id, start_date, end_date):
    """
    Gets and filters "Lead Form" campaign data for a specific period.
    """
    logger.info(f"🔄 Getting data for period: {start_date} to {end_date}...")
    try:
        # Initialize Facebook API
        initialize_facebook_api()
        
        ad_account = AdAccount(ad_account_id)
        
        campaign_fields = [
            'id', 'account_id', 'name', 'objective', 'status', 'effective_status',
            'buying_type', 'start_time', 'stop_time', 'created_time', 'daily_budget',
            'lifetime_budget', 'budget_remaining', 'special_ad_categories',
        ]

        insights_fields = [
            'spend', 'impressions', 'reach', 'frequency', 'actions', 
            'cost_per_action_type', 'action_values', 'cpm', 'inline_link_clicks', 
            'cost_per_inline_link_click', 'inline_link_click_ctr', 'clicks', 'cpc', 'ctr',
        ]

        params_to_get = {
            'time_range': {'since': str(start_date), 'until': str(end_date)},
            'level': 'campaign',
        }
        
        campaigns = ad_account.get_campaigns(fields=campaign_fields)
        extracted_data = []

        for campaign in campaigns:
            campaign_name = campaign.get('name', '').lower()

            if 'lead form' not in campaign_name:
                if 'trafico' in campaign_name or 'tráfico' in campaign_name:
                    logger.info(f"🟡 Skipping Traffic campaign: {campaign.get('name')}")
                elif 'conversion' in campaign_name:
                    logger.info(f"🟡 Skipping Conversion campaign (pending analysis): {campaign.get('name')}")
                else:
                    logger.info(f"🟡 Skipping campaign (not Lead Form): {campaign.get('name')}")
                continue

            logger.info(f"🟢 Processing Lead Form campaign: {campaign.get('name')}")
            insights = campaign.get_insights(fields=insights_fields, params=params_to_get)
            
            if insights:
                resultados_num, indicador_res, indicador_real, costo_por_resultado = _parse_results(campaign, insights)
                
                budget_type = "Daily" if campaign.get('daily_budget') else "Total"
                budget_value = campaign.get('daily_budget') or campaign.get('lifetime_budget', 0)
                actions_list = insights[0].get('actions', [])
                shop_clicks_action = next((a for a in actions_list if a['action_type'] == 'shop_clicks'), None)
                shop_clicks_value = int(shop_clicks_action['value']) if shop_clicks_action else 0

                campaign_info = {
                    'Campaign ID': campaign.get('id'),
                    'Inicio del informe': start_date.strftime('%Y-%m-%d'),
                    'Fin del informe': end_date.strftime('%Y-%m-%d'),
                    'Nombre de la campaña': campaign.get('name'),
                    'Objective': campaign.get('objective'),
                    'Entrega de la campaña': campaign.get('effective_status'),
                    'Resultados': resultados_num,
                    'Indicador de resultado': indicador_res,
                    'Indicador de resultado _REAL': indicador_real,
                    'Alcance': int(insights[0].get('reach', 0)),
                    'Frecuencia': float(insights[0].get('frequency', 0)),
                    'Costo por resultados (CLP)': costo_por_resultado,
                    'Presupuesto del conjunto de anuncios': int(budget_value) / 100,
                    'Tipo de presupuesto del conjunto de anuncios': budget_type,
                    'Importe gastado (CLP)': float(insights[0].get('spend', 0)),
                    'Finalización': campaign.get('stop_time', 'Abierta'),
                    'Impresiones': int(insights[0].get('impressions', 0)),
                    'CPM (costo por mil impresiones) (CLP)': float(insights[0].get('cpm', 0)),
                    'Clics en el enlace': int(insights[0].get('inline_link_clicks', 0)),
                    'shop_clicks': shop_clicks_value,
                    'CPC (costo por clic en el enlace) (CLP)': float(insights[0].get('cost_per_inline_link_click', 0)),
                    'CTR (porcentaje de clics en el enlace)': float(insights[0].get('inline_link_click_ctr', 0)),
                    'Clics (todos)': int(insights[0].get('clicks', 0)),
                    'CTR (todos)': float(insights[0].get('ctr', 0)),
                    'CPC (todos) (CLP)': float(insights[0].get('cpc', 0)),
                }
                extracted_data.append(campaign_info)
        
        if not extracted_data:
            logger.info(f"🟡 No 'Lead Form' campaign data found for the period.")
            return pd.DataFrame()

        df = pd.DataFrame(extracted_data)
        
        final_column_order = [
            'Campaign ID', 'Inicio del informe', 'Fin del informe', 'Nombre de la campaña', 'Objective', 'Entrega de la campaña',
            'Resultados', 'Indicador de resultado', 'Indicador de resultado _REAL', 'Alcance', 'Frecuencia',
            'Costo por resultados (CLP)', 'Presupuesto del conjunto de anuncios', 'Tipo de presupuesto del conjunto de anuncios',
            'Importe gastado (CLP)', 'Finalización', 'Impresiones', 'CPM (costo por mil impresiones) (CLP)',
            'Clics en el enlace', 'shop_clicks', 'CPC (costo por clic en el enlace) (CLP)',
            'CTR (porcentaje de clics en el enlace)', 'Clics (todos)', 'CTR (todos)', 'CPC (todos) (CLP)'
        ]
        
        df = df.reindex(columns=final_column_order)

        logger.info(f"✅ Lead Form data obtained and processed for {len(extracted_data)} campaigns.")
        return df

    except Exception as e:
        logger.error(f"❌ Error getting campaign data: {e}")
        logger.error(traceback.format_exc())
        return pd.DataFrame()

# === Input Schemas for Tools ===

class ListClientsInput(BaseModel):
    """Input schema for list_available_clients_tool."""
    user_id: int = Field(..., description="User ID (foreign key to users table)")

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
    # Create date period in YYYY-MM format
    date_period = start_date.strftime("%Y-%m")
    query_hash = hashlib.sha256(f"campaign_data_{ad_account_id}_{campaign_type}_{start_date}_{end_date}".encode()).hexdigest()
    
    try:
        # Check for valid cache entry
        cache_entry = db.query(ApiCache).filter(
            and_(
                ApiCache.ad_account_id == ad_account_id,
                ApiCache.date_period == date_period,
                ApiCache.query_hash == query_hash
            )
        ).first()
        
        if cache_entry:
            logger.info(f"Using cached data for {ad_account_id} - {date_period}")
            return cache_entry.result_json
        else:
            logger.info(f"No valid cache found for {ad_account_id} - {date_period}")
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
    # Create date period in YYYY-MM format
    date_period = start_date.strftime("%Y-%m")
    query_hash = hashlib.sha256(f"campaign_data_{ad_account_id}_{campaign_type}_{start_date}_{end_date}".encode()).hexdigest()
    
    try:
        # Remove any existing cache entries for this account and period
        db.query(ApiCache).filter(
            and_(
                ApiCache.ad_account_id == ad_account_id,
                ApiCache.date_period == date_period
            )
        ).delete()
        
        # Create new cache entry
        cache_entry = ApiCache(
            ad_account_id=ad_account_id,
            date_period=date_period,
            query_hash=query_hash,
            result_json=data
        )
        
        db.add(cache_entry)
        db.commit()
        
        logger.info(f"Saved data to cache: {ad_account_id} - {date_period}")
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
    name: str = "list_available_clients"
    description: str = "List all available Facebook advertising accounts for a specific user. Use this to show the user which clients/accounts they can analyze."
    args_schema: type = ListClientsInput
    
    def _run(self, user_id: int) -> str:
        """
        Execute the tool to list available clients.
        
        Args:
            user_id: User ID (foreign key to users table)
        
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
    name: str = "facebook_ads_analysis"
    description: str = "Analyze Facebook advertising campaign data for a specific account. Returns performance data for the last two months with caching for efficiency."
    args_schema: type = FacebookAnalysisInput
    
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
