# === File: src/azure_llm.py ===

import pandas as pd
from openai import AzureOpenAI
from config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_API_VERSION, AZURE_OPENAI_DEPLOYMENT_NAME

def analizar_dataframes_con_llm(df_mes_actual, df_mes_anterior, nombre_mes_actual, nombre_mes_anterior):
    """
    Envía dos DataFrames a un LLM en Azure para obtener un análisis comparativo.
    """
    print("\n🚀 Iniciando análisis con Azure OpenAI (GPT-4o)...")
    try:
        # Asegurarnos de que las credenciales se cargaron desde config.py
        if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME]):
            print("❌ Error: Faltan credenciales de Azure OpenAI en el archivo .env o config.py.")
            return None

        client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_API_VERSION
        )
        
        tabla_n = df_mes_actual.to_markdown(index=False)
        tabla_n_minus_1 = df_mes_anterior.to_markdown(index=False)

        system_prompt = "Eres un experto en Marketing Digital y análisis de datos de campañas de Facebook Ads."
        
        user_prompt = f"""
        Tienes que analizar los resultados de la tabla del mes de {nombre_mes_actual} (tabla_n) y la del mes de {nombre_mes_anterior} (tabla_n-1) y sacar las siguientes conclusiones:
        
        1. Separa las campañas Lead Form.
        2. Compara los costo por resultado de cada una de las campañas.
        3. Compara los CTR (porcentaje de clics en el enlace) de cada una de las campañas.
        4. Compara la cantidad de resultados (leads) de cada una de las campañas. ¿Por qué hubo más o menos resultados respecto al mes anterior (mayor o menor inversión, mayor o menor costo por resultado)?
        5. Haz un listado de las principales medidas a realizar para mejorar el performance.

        Aquí están los datos:

        ## Tabla N ({nombre_mes_actual}):
        {tabla_n}

        ## Tabla N-1 ({nombre_mes_anterior}):
        {tabla_n_minus_1}
        """

        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        print("✅ Análisis completado exitosamente.")
        return response.choices[0].message.content

    except Exception as e:
        print(f"❌ Error al conectar con Azure OpenAI: {e}")
        return None