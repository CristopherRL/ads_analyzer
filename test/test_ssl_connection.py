#!/usr/bin/env python3
"""
Script simple para probar conectividad SSL a Facebook.
Útil para diagnosticar problemas de red/SSL.
"""

import ssl
import socket
import requests
import urllib3
from urllib.parse import urlparse

# Deshabilitar warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_ssl_connection(hostname, port=443):
    """Probar conexión SSL básica"""
    print(f"🔒 Probando conexión SSL a {hostname}:{port}")
    
    try:
        # Crear contexto SSL
        context = ssl.create_default_context()
        
        # Conectar
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                print(f"✅ Conexión SSL exitosa")
                print(f"   Protocolo: {ssock.version()}")
                print(f"   Cipher: {ssock.cipher()}")
                return True
                
    except ssl.SSLError as e:
        print(f"❌ Error SSL: {e}")
        return False
    except socket.timeout:
        print(f"❌ Timeout de conexión")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_http_request(url, verify_ssl=True):
    """Probar petición HTTP"""
    print(f"🌐 Probando petición HTTP a {url}")
    
    try:
        response = requests.get(url, timeout=10, verify=verify_ssl)
        print(f"✅ Petición exitosa - Status: {response.status_code}")
        return True
    except requests.exceptions.SSLError as e:
        print(f"❌ Error SSL en petición: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Error de conexión: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Función principal"""
    print("🔧 Script de Diagnóstico SSL/Conectividad")
    print("=" * 50)
    
    # Probar conectividad SSL básica
    ssl_ok = test_ssl_connection("graph.facebook.com")
    
    print()
    
    # Probar petición HTTP con SSL
    http_ssl_ok = test_http_request("https://graph.facebook.com/v19.0/me", verify_ssl=True)
    
    print()
    
    # Probar petición HTTP sin verificar SSL
    http_no_ssl_ok = test_http_request("https://graph.facebook.com/v19.0/me", verify_ssl=False)
    
    print()
    print("=" * 50)
    print("📋 RESUMEN:")
    print(f"   SSL Básico: {'✅ OK' if ssl_ok else '❌ ERROR'}")
    print(f"   HTTP con SSL: {'✅ OK' if http_ssl_ok else '❌ ERROR'}")
    print(f"   HTTP sin SSL: {'✅ OK' if http_no_ssl_ok else '❌ ERROR'}")
    
    if not ssl_ok:
        print("\n💡 SOLUCIONES:")
        print("   1. Actualizar certificados SSL del sistema")
        print("   2. Verificar configuración de proxy")
        print("   3. Usar VPN si estás en red corporativa")
        print("   4. Configurar variables de entorno:")
        print("      set SSL_VERIFY=False")
        print("      set REQUESTS_CA_BUNDLE=")
    
    if http_no_ssl_ok and not http_ssl_ok:
        print("\n💡 El problema es específico de verificación SSL")
        print("   Puedes usar la aplicación con SSL deshabilitado")

if __name__ == "__main__":
    main()
