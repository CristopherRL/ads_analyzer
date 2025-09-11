# === File: main.py ===

from datetime import datetime
from dateutil.relativedelta import relativedelta
from src.facebook_api import initialize_facebook_api, get_campaign_data_for_period
from src.azure_llm import analizar_dataframes_con_llm
from config import FB_AD_ACCOUNT_ID

def run_analysis():
    """Función principal que orquesta todo el proceso."""
    
    # 1. Conectarse a la API de Facebook
    initialize_facebook_api()

    # 2. Calcular los períodos de tiempo
    today = datetime.today().date()
    last_month_end = today.replace(day=1) - relativedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    prev_month_end = last_month_start - relativedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    # 3. Obtener datos de campañas (solo Lead Form)
    df_last_month = get_campaign_data_for_period(FB_AD_ACCOUNT_ID, last_month_start, last_month_end)
    df_prev_month = get_campaign_data_for_period(FB_AD_ACCOUNT_ID, prev_month_start, prev_month_end)

    # 4. Analizar con LLM y guardar el resultado
    if not df_last_month.empty and not df_prev_month.empty:
        nombre_mes_actual = last_month_start.strftime("%B de %Y")
        nombre_mes_anterior = prev_month_start.strftime("%B de %Y")
        
        conclusion_llm = analizar_dataframes_con_llm(df_last_month, df_prev_month, nombre_mes_actual, nombre_mes_anterior)
        
        if conclusion_llm:
            print("\n\n--- CONCLUSIONES DEL EXPERTO EN MARKETING DIGITAL (IA) ---\n")
            print(conclusion_llm)
            
            # Construir y guardar el archivo de reporte
            id_client = FB_AD_ACCOUNT_ID.replace('act_', '')
            action_type = "Lead_Form"
            period_str = f"{prev_month_start.strftime('%Y_%m')}-{last_month_start.strftime('%Y_%m')}"
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"reporte_fb_ads__act_{id_client}__{action_type}_{period_str}_{timestamp_str}.txt"
            
            try:
                with open(file_name, "w", encoding="utf-8") as f:
                    f.write(conclusion_llm)
                print(f"\n✅ Conclusión guardada exitosamente en el archivo: {file_name}")
            except Exception as e:
                print(f"\n❌ Error al guardar el archivo de conclusión: {e}")
    else:
        print("\n🟡 No se generó análisis de IA porque falta información de Lead Form en uno o ambos meses.")

if __name__ == "__main__":
    run_analysis()