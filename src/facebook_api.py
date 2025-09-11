# === File: src/facebook_api.py ===

import pandas as pd
import traceback
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from config import FB_APP_ID, FB_APP_SECRET, FB_ACCESS_TOKEN, ACTION_MAP

def initialize_facebook_api():
    """Establece la conexión con la API de Facebook."""
    try:
        FacebookAdsApi.init(FB_APP_ID, FB_APP_SECRET, FB_ACCESS_TOKEN)
        print("✅ Conexión con la API de Facebook exitosa.")
    except Exception as e:
        print(f"❌ Error al inicializar la API de Facebook: {e}")
        raise

def _parse_results(campaign, campaign_insights):
    """
    Función auxiliar privada para determinar el resultado principal de una campaña,
    basándose en palabras clave en el nombre de la campaña.
    """
    if not campaign_insights or not campaign_insights[0].get('actions'):
        return 0, 'N/A', 'N/A', 0.0

    insight_data = campaign_insights[0]
    actions = insight_data.get('actions', [])
    cost_per_action = insight_data.get('cost_per_action_type', [])
    campaign_name = campaign.get('name', '').lower()

    target_indicator = ''
    if 'conversion' in campaign_name:
        target_indicator = 'conversions:submit_application_website'
    elif 'lead form' in campaign_name:
        target_indicator = 'actions:onsite_conversion.lead_grouped'
    elif 'tráfico' in campaign_name or 'trafico' in campaign_name:
        target_indicator = 'actions:link_click'
    else:
        target_indicator = 'conversions:submit_application_website'

    if target_indicator:
        possible_api_names = ACTION_MAP.get(target_indicator, [])
        for api_name in possible_api_names:
            action_obj = next((a for a in actions if a['action_type'] == api_name), None)
            if action_obj:
                result_count = int(action_obj['value'])
                cost_obj = next((c for c in cost_per_action if c['action_type'] == api_name), None)
                cost_per_result = float(cost_obj['value']) if cost_obj else 0.0
                return result_count, target_indicator, api_name, cost_per_result

    print(f"🟡 ADVERTENCIA: No se encontró acción principal para '{campaign.get('name')}'. Usando fallback.")
    if cost_per_action:
        sorted_costs = sorted(cost_per_action, key=lambda x: float(x.get('value', 0)), reverse=True)
        fallback_action = sorted_costs[0]
        fallback_type = fallback_action['action_type']
        fallback_cost = float(fallback_action['value'])
        fallback_count_obj = next((ac for ac in actions if ac['action_type'] == fallback_type), None)
        fallback_count = int(fallback_count_obj['value']) if fallback_count_obj else 0
        return fallback_count, f"fallback:{fallback_type}", fallback_type, fallback_cost

    return 0, 'N/A', 'N/A', 0.0


def get_campaign_data_for_period(ad_account_id, start_date, end_date):
    """
    Obtiene y filtra los datos de las campañas de "Lead Form" para un período específico.
    """
    print(f"\n🔄 Obteniendo datos para el período: {start_date} a {end_date}...")
    try:
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
                    print(f"🟡 Omitiendo campaña de Tráfico: {campaign.get('name')}")
                elif 'conversion' in campaign_name:
                    print(f"🟡 Omitiendo campaña de Conversión (pendiente de análisis): {campaign.get('name')}")
                else:
                    print(f"🟡 Omitiendo campaña (no es de Lead Form): {campaign.get('name')}")
                continue

            print(f"🟢 Procesando campaña de Lead Form: {campaign.get('name')}")
            insights = campaign.get_insights(fields=insights_fields, params=params_to_get)
            
            if insights:
                resultados_num, indicador_res, indicador_real, costo_por_resultado = _parse_results(campaign, insights)
                
                budget_type = "Diario" if campaign.get('daily_budget') else "Total"
                budget_value = campaign.get('daily_budget') or campaign.get('lifetime_budget', 0)
                actions_list = insights[0].get('actions', [])
                shop_clicks_action = next((a for a in actions_list if a['action_type'] == 'shop_clicks'), None)
                shop_clicks_value = int(shop_clicks_action['value']) if shop_clicks_action else 0

                campaign_info = {
                    'ID Campaña': campaign.get('id'),
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
            print(f"🟡 No se encontraron datos de campañas de 'Lead Form' para el período.")
            return pd.DataFrame()

        df = pd.DataFrame(extracted_data)
        
        final_column_order = [
            'ID Campaña', 'Inicio del informe', 'Fin del informe', 'Nombre de la campaña', 'Objective', 'Entrega de la campaña',
            'Resultados', 'Indicador de resultado', 'Indicador de resultado _REAL', 'Alcance', 'Frecuencia',
            'Costo por resultados (CLP)', 'Presupuesto del conjunto de anuncios', 'Tipo de presupuesto del conjunto de anuncios',
            'Importe gastado (CLP)', 'Finalización', 'Impresiones', 'CPM (costo por mil impresiones) (CLP)',
            'Clics en el enlace', 'shop_clicks', 'CPC (costo por clic en el enlace) (CLP)',
            'CTR (porcentaje de clics en el enlace)', 'Clics (todos)', 'CTR (todos)', 'CPC (todos) (CLP)'
        ]
        
        df = df.reindex(columns=final_column_order)

        print(f"✅ Datos de Lead Form obtenidos y procesados para {len(extracted_data)} campañas.")
        return df

    except Exception as e:
        print(f"❌ Error al obtener datos de campaña: {e}")
        traceback.print_exc()
        return pd.DataFrame()