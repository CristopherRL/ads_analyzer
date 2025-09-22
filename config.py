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
# Base endpoint (without /openai/deployments/ path)
AZURE_OPENAI_BASE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
# Full endpoint with deployment path (constructed automatically)
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")  # Keep for backward compatibility
AZURE_INFERENCE_CREDENTIAL = os.getenv("AZURE_INFERENCE_CREDENTIAL")  # New credential for LangChain
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_API_VERSION = "2024-12-01-preview"

# --- Credenciales de PostgreSQL ---
DATABASE_CONNECTION_STRING = os.getenv('DATABASE_CONNECTION_STRING')


# --- Application Configuration ---
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
# --- Logging Configuration ---
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- LangChain and Agent Configuration ---
# Memory configuration
MEMORY_TEMPERATURE = float(os.getenv('MEMORY_TEMPERATURE', '0.1'))
MEMORY_MAX_TOKEN_LIMIT = int(os.getenv('MEMORY_MAX_TOKEN_LIMIT', '2000'))
# Agent configuration  
AGENT_TEMPERATURE = float(os.getenv('AGENT_TEMPERATURE', '0.7'))
AGENT_MAX_TOKENS = int(os.getenv('AGENT_MAX_TOKENS', '2000'))
AGENT_MAX_ITERATIONS = int(os.getenv('AGENT_MAX_ITERATIONS', '5'))
# Cache configuration
CACHE_EXPIRATION_HOURS = int(os.getenv('CACHE_EXPIRATION_HOURS', '1'))
# --- Prompts Configuration ---
SYSTEM_PROMPT_SOURCE = os.getenv('SYSTEM_PROMPT_SOURCE', 'database')  # 'default' or 'database'
DEFAULT_PROMPT_FILE = os.getenv('DEFAULT_PROMPT_FILE', 'src/prompts/default_system_prompt.txt')