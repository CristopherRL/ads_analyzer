#!/usr/bin/env python3
"""
Script alternativo para probar Facebook API usando requests directamente.
Evita problemas con el SDK de Facebook y SSL.
"""

import os
import sys
import requests
import urllib3
from dotenv import load_dotenv

# Deshabilitar warnings SSL
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
        return False
    
    return True

def test_facebook_api_direct():
    """Probar Facebook API usando requests directamente"""
    print("🔍 Probando Facebook API con requests directo...")
    
    try:
        access_token = os.getenv('FB_ACCESS_TOKEN')
        ad_account_id = os.getenv('FB_AD_ACCOUNT_ID')
        
        # Asegurar formato correcto del ID
        if not ad_account_id.startswith('act_'):
            ad_account_id = f"act_{ad_account_id}"
        
        print(f"🎯 Probando acceso a cuenta: {ad_account_id}")
        
        # URL para obtener información de la cuenta
        url = f"https://graph.facebook.com/v19.0/{ad_account_id}"
        
        # Parámetros
        params = {
            'access_token': access_token,
            'fields': 'id,name,account_status'
        }
        
        # Hacer petición sin verificar SSL
        response = requests.get(url, params=params, verify=False, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Conexión exitosa a la cuenta: {data.get('name', 'Sin nombre')}")
            print(f"   ID: {data.get('id')}")
            print(f"   Estado: {data.get('account_status')}")
            return True
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
            
    except requests.exceptions.SSLError as e:
        print(f"❌ Error SSL: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Error de conexión: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def test_facebook_campaigns_direct():
    """Probar consulta de campañas usando requests directamente"""
    print("\n📊 Probando consulta de campañas...")
    
    try:
        access_token = os.getenv('FB_ACCESS_TOKEN')
        ad_account_id = os.getenv('FB_AD_ACCOUNT_ID')
        
        # Asegurar formato correcto del ID
        if not ad_account_id.startswith('act_'):
            ad_account_id = f"act_{ad_account_id}"
        
        # URL para obtener campañas
        url = f"https://graph.facebook.com/v19.0/{ad_account_id}/campaigns"
        
        # Parámetros
        params = {
            'access_token': access_token,
            'fields': 'id,name,status',
            'limit': 5
        }
        
        # Hacer petición sin verificar SSL
        response = requests.get(url, params=params, verify=False, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            campaigns = data.get('data', [])
            
            if campaigns:
                print(f"   ✅ Se encontraron {len(campaigns)} campañas:")
                for i, campaign in enumerate(campaigns, 1):
                    print(f"      {i}. {campaign.get('name')} (ID: {campaign.get('id')})")
            else:
                print("   ⚠️  No se encontraron campañas en esta cuenta")
            
            return True
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error consultando campañas: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Script de Prueba Facebook API (Método Directo)")
    print("=" * 60)
    
    # Cargar variables de entorno
    if not load_environment():
        sys.exit(1)
    
    # Probar API de Facebook
    api_ok = test_facebook_api_direct()
    
    if api_ok:
        # Probar consulta de campañas
        campaigns_ok = test_facebook_campaigns_direct()
    else:
        campaigns_ok = False
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE PRUEBAS:")
    print(f"   Facebook API: {'✅ OK' if api_ok else '❌ ERROR'}")
    print(f"   Consulta Campañas: {'✅ OK' if campaigns_ok else '❌ ERROR'}")
    
    if api_ok and campaigns_ok:
        print("\n🎉 ¡Facebook API funciona correctamente!")
        print("💡 El problema está en el SDK de Facebook, no en la conectividad")
        sys.exit(0)
    else:
        print("\n⚠️  Hay problemas con la API de Facebook")
        sys.exit(1)

if __name__ == "__main__":
    main()
