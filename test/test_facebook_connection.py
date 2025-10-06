#!/usr/bin/env python3
"""
Script de prueba para verificar la conexión a Facebook Marketing API.
Ejecutar: python test_facebook_connection.py
"""

import os
import sys
import ssl
import urllib3
from dotenv import load_dotenv
from facebook_business import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.exceptions import FacebookRequestError

# Configurar SSL para entornos corporativos
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def load_environment():
    """Cargar variables de entorno desde .env"""
    load_dotenv()
    
    required_vars = [
        'FB_APP_ID',
        'FB_APP_SECRET', 
        'FB_ACCESS_TOKEN',
        'FB_AD_ACCOUNT_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Variables de entorno faltantes: {', '.join(missing_vars)}")
        print("Asegúrate de tener un archivo .env con estas variables:")
        for var in missing_vars:
            print(f"  {var}=tu_valor_aqui")
        return False
    
    return True

def test_network_connectivity():
    """Probar conectividad básica a Facebook"""
    print("🌐 Probando conectividad de red...")
    
    try:
        import requests
        import urllib3
        
        # Configurar SSL context más permisivo
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Probar conectividad básica
        response = requests.get(
            'https://graph.facebook.com/v19.0/me',
            timeout=10,
            verify=False
        )
        
        if response.status_code in [200, 400, 401]:  # 400/401 son esperados sin token
            print("✅ Conectividad básica a Facebook OK")
            return True
        else:
            print(f"⚠️  Respuesta inesperada: {response.status_code}")
            return False
            
    except requests.exceptions.SSLError as e:
        print(f"❌ Error SSL: {e}")
        print("💡 Sugerencia: Problema de certificados SSL")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Error de conexión: {e}")
        print("💡 Sugerencia: Verificar conectividad a internet o proxy")
        return False
    except Exception as e:
        print(f"❌ Error de red: {e}")
        return False

def test_facebook_api_connection():
    """Probar conexión a Facebook Marketing API"""
    print("🔍 Probando conexión a Facebook Marketing API...")
    
    # Primero probar conectividad básica
    if not test_network_connectivity():
        print("❌ No se puede continuar sin conectividad básica")
        return False
    
    try:
        # Inicializar API
        app_id = os.getenv('FB_APP_ID')
        app_secret = os.getenv('FB_APP_SECRET')
        access_token = os.getenv('FB_ACCESS_TOKEN')
        ad_account_id = os.getenv('FB_AD_ACCOUNT_ID')
        
        print(f"📋 Configuración:")
        print(f"  App ID: {app_id}")
        print(f"  App Secret: {'*' * len(app_secret) if app_secret else 'NO CONFIGURADO'}")
        print(f"  Access Token: {'*' * 20}...{access_token[-10:] if access_token else 'NO CONFIGURADO'}")
        print(f"  Ad Account ID: {ad_account_id}")
        print()
        
        # Configurar SSL deshabilitado para Facebook Ads API
        import ssl
        import urllib3
        
        # Crear contexto SSL que no verifica certificados
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Configurar urllib3 para no verificar SSL
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Inicializar Facebook Ads API con configuración SSL personalizada
        FacebookAdsApi.init(app_id, app_secret, access_token)
        
        # Configurar el cliente HTTP para no verificar SSL
        import requests
        from facebook_business.api import FacebookAdsApi
        
        # Obtener la instancia de API y configurar SSL
        api = FacebookAdsApi.get_default_api()
        if hasattr(api, '_session'):
            api._session.verify = False
        
        print("✅ Facebook Ads API inicializada correctamente (SSL deshabilitado)")
        
        # Probar acceso a la cuenta publicitaria
        if not ad_account_id:
            print("❌ FACEBOOK_AD_ACCOUNT_ID no configurado")
            return False
            
        # Asegurar formato correcto del ID
        if not ad_account_id.startswith('act_'):
            ad_account_id = f"act_{ad_account_id}"
        
        print(f"🎯 Probando acceso a cuenta: {ad_account_id}")
        ad_account = AdAccount(ad_account_id)
        
        # Probar consulta básica
        account_info = ad_account.api_get(fields=['id', 'name', 'account_status'])
        print(f"✅ Conexión exitosa a la cuenta: {account_info.get('name', 'Sin nombre')}")
        print(f"   ID: {account_info.get('id')}")
        print(f"   Estado: {account_info.get('account_status')}")
        
        # Probar consulta de campañas
        print("\n📊 Probando consulta de campañas...")
        campaigns = ad_account.get_campaigns(fields=['id', 'name', 'status'], limit=5)
        campaign_count = 0
        
        for campaign in campaigns:
            campaign_count += 1
            print(f"   Campaña {campaign_count}: {campaign.get('name')} (ID: {campaign.get('id')})")
        
        if campaign_count == 0:
            print("   ⚠️  No se encontraron campañas en esta cuenta")
        else:
            print(f"   ✅ Se encontraron {campaign_count} campañas")
        
        return True
        
    except FacebookRequestError as e:
        print(f"❌ Error de Facebook API:")
        print(f"   Código: {e.api_error_code()}")
        print(f"   Mensaje: {e.api_error_message()}")
        print(f"   Tipo: {e.api_error_type()}")
        
        # Sugerencias específicas según el error
        error_code = e.api_error_code()
        if error_code == 200:
            print("\n💡 Sugerencia: Verifica que FACEBOOK_APP_ID sea correcto")
        elif error_code == 190:
            print("\n💡 Sugerencia: El access token ha expirado o es inválido")
        elif error_code == 100:
            print("\n💡 Sugerencia: Verifica que tengas permisos en la cuenta publicitaria")
        
        return False
        
    except Exception as e:
        error_str = str(e)
        print(f"❌ Error inesperado: {error_str}")
        
        # Detectar errores SSL específicos
        if "SSL" in error_str or "SSLError" in error_str:
            print("\n💡 Soluciones para errores SSL:")
            print("   1. Verificar configuración de proxy corporativo")
            print("   2. Actualizar certificados SSL del sistema")
            print("   3. Configurar variables de entorno SSL:")
            print("      export SSL_VERIFY=False")
            print("      export REQUESTS_CA_BUNDLE=")
            print("   4. Usar VPN si estás en red corporativa")
        elif "Connection" in error_str:
            print("\n💡 Soluciones para errores de conexión:")
            print("   1. Verificar conectividad a internet")
            print("   2. Comprobar configuración de firewall")
            print("   3. Verificar configuración de proxy")
        
        return False

def test_azure_key_vault_integration():
    """Probar integración con Azure Key Vault (opcional)"""
    print("\n🔐 Probando integración con Azure Key Vault...")
    
    try:
        from azure.keyvault.secrets import SecretClient
        from azure.identity import DefaultAzureCredential
        
        # Solo probar si está configurado
        key_vault_url = os.getenv('AZURE_KEY_VAULT_URL')
        if not key_vault_url:
            print("   ⚠️  AZURE_KEY_VAULT_URL no configurado - saltando prueba")
            return True
        
        print(f"   🔗 Key Vault URL: {key_vault_url}")
        
        # Probar conexión
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=key_vault_url, credential=credential)
        
        # Listar secretos (solo los primeros 5)
        secrets = list(client.list_properties_of_secrets(max_page_size=5))
        print(f"   ✅ Conexión exitosa - {len(secrets)} secretos encontrados")
        
        return True
        
    except ImportError:
        print("   ⚠️  Azure Key Vault SDK no instalado - saltando prueba")
        return True
    except Exception as e:
        print(f"   ❌ Error con Azure Key Vault: {str(e)}")
        return False

def main():
    """Función principal"""
    print("🚀 Script de Prueba de Conexión Facebook Marketing API")
    print("=" * 60)
    
    # Cargar variables de entorno
    if not load_environment():
        sys.exit(1)
    
    # Probar conexión a Facebook API
    facebook_ok = test_facebook_api_connection()
    
    # Probar Azure Key Vault (opcional)
    azure_ok = test_azure_key_vault_integration()
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE PRUEBAS:")
    print(f"   Facebook API: {'✅ OK' if facebook_ok else '❌ ERROR'}")
    print(f"   Azure Key Vault: {'✅ OK' if azure_ok else '❌ ERROR'}")
    
    if facebook_ok and azure_ok:
        print("\n🎉 ¡Todas las conexiones funcionan correctamente!")
        sys.exit(0)
    else:
        print("\n⚠️  Hay problemas de configuración que resolver")
        sys.exit(1)

if __name__ == "__main__":
    main()
