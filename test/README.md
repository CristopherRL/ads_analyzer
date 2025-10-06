# Tests - Ads Analyzer

Esta carpeta contiene todos los scripts de prueba para verificar la configuración y conectividad del sistema.

## 📁 Archivos de Prueba

### 🔧 Scripts de Diagnóstico

#### `test_facebook_direct.py`
**Script principal recomendado** - Prueba Facebook API usando requests directamente
```bash
python test_facebook_direct.py
```
- ✅ Evita problemas con SDK de Facebook
- ✅ Usa SSL deshabilitado
- ✅ Prueba conectividad y consulta de campañas

#### `test_facebook_connection.py`
Script completo con SDK de Facebook
```bash
python test_facebook_connection.py
```
- ✅ Prueba completa con SDK oficial
- ✅ Diagnóstico de conectividad
- ✅ Integración con Azure Key Vault

#### `test_ssl_connection.py`
Script específico para problemas SSL
```bash
python test_ssl_connection.py
```
- ✅ Diagnóstico de problemas SSL
- ✅ Pruebas de conectividad básica
- ✅ Identificación de problemas de certificados

#### `test_campaign_filtering.py`
Script para probar filtrado de campañas
```bash
python test_campaign_filtering.py
```
- ✅ Prueba lógica de filtrado de campañas
- ✅ Verifica detección de tipos de campaña
- ✅ Debugging de problemas de filtrado

## 🚀 Uso Rápido

### 1. Verificar Configuración
```bash
python test_facebook_direct.py
```

### 2. Si hay problemas SSL
```bash
python test_ssl_connection.py
```

### 3. Prueba completa
```bash
python test_facebook_connection.py
```

## 🔧 Configuración Requerida

### Variables de Entorno (.env)
```env
# Facebook API
FB_APP_ID=tu_app_id
FB_APP_SECRET=tu_app_secret
FB_ACCESS_TOKEN=tu_access_token
FB_AD_ACCOUNT_ID=act_123456789

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://tu-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=tu_api_key
AZURE_OPENAI_DEPLOYMENT_NAME=tu_deployment

# Base de Datos
DATABASE_CONNECTION_STRING=postgresql://user:pass@host:port/db
```

### Variables SSL (para problemas de conectividad)
```bash
# Windows
set SSL_VERIFY=False
set REQUESTS_CA_BUNDLE=

# Linux/Mac
export SSL_VERIFY=False
export REQUESTS_CA_BUNDLE=
```

## 🛠️ Solución de Problemas

### Error: "FB_APP_ID not configured"
- Verificar que las variables en `.env` coincidan con `config.py`
- Ejecutar `python test_facebook_direct.py` para verificar

### Error: "SSL: UNEXPECTED_EOF_WHILE_READING"
- Configurar variables SSL como se muestra arriba
- Usar `test_ssl_connection.py` para diagnóstico

### Error: "Provide valid app ID"
- Verificar `FB_APP_ID` en `.env`
- Comprobar que la app esté activa en Facebook Developer Console

## 📝 Próximos Pasos

1. **Ejecutar tests** para verificar configuración
2. **Corregir errores** según las sugerencias
3. **Probar aplicación** con `uvicorn main:app --reload`
4. **Verificar logs** para problemas adicionales
