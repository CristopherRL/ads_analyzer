# === File: config.py ===

import os
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# --- Credenciales de Facebook ---
FB_APP_ID = os.getenv('FACEBOOK_APP_ID')
FB_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET')
FB_ACCESS_TOKEN = os.getenv('FACEBOOK_ACCESS_TOKEN')
FB_AD_ACCOUNT_ID = os.getenv('FACEBOOK_AD_ACCOUNT_ID')

# --- Credenciales de Azure OpenAI ---
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_API_VERSION = "2024-02-01"

# --- Credenciales de PostgreSQL ---
DATABASE_CONNECTION_STRING = os.getenv('DATABASE_CONNECTION_STRING')

# --- Configuración de la Aplicación ---
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'