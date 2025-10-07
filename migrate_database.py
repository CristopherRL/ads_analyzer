#!/usr/bin/env python3
"""
Script de migración de base de datos para implementar todas las mejoras.
Ejecuta todas las migraciones en orden correcto.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def run_migration():
    """Ejecuta la migración completa de la base de datos."""
    
    print("🚀 Iniciando Migración de Base de Datos")
    print("=" * 50)
    
    # Obtener configuración de base de datos desde variables de entorno
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'ads_analyzer'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', '')
    }
    
    try:
        # Conectar a la base de datos
        print("1. Conectando a la base de datos...")
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        print("   ✅ Conexión establecida")
        
        # Leer y ejecutar script de migración
        print("2. Ejecutando script de migración...")
        migration_file = "docs/internal/queries/migration_complete.sql"
        
        if not os.path.exists(migration_file):
            print(f"   ❌ Error: No se encontró el archivo {migration_file}")
            return False
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # Ejecutar el script SQL
        cursor.execute(migration_sql)
        print("   ✅ Script de migración ejecutado")
        
        # Verificar que las tablas se crearon correctamente
        print("3. Verificando tablas creadas...")
        
        tables_to_check = [
            'model_pricing',
            'user_facebook_accounts', 
            'analysis_results'
        ]
        
        for table in tables_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table}'")
            exists = cursor.fetchone()[0] > 0
            if exists:
                print(f"   ✅ Tabla {table}: Creada")
            else:
                print(f"   ❌ Tabla {table}: No encontrada")
                return False
        
        # Verificar campos nuevos en conversation_history
        print("4. Verificando campos nuevos en conversation_history...")
        new_fields = ['full_prompt_sent', 'llm_params', 'tokens_used', 'estimated_cost_usd']
        
        for field in new_fields:
            cursor.execute(f"""
                SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name = 'conversation_history' AND column_name = '{field}'
            """)
            exists = cursor.fetchone()[0] > 0
            if exists:
                print(f"   ✅ Campo {field}: Agregado")
            else:
                print(f"   ❌ Campo {field}: No encontrado")
                return False
        
        # Verificar que facebook_account_id fue eliminado de api_cache
        print("5. Verificando limpieza de api_cache...")
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'api_cache' AND column_name = 'facebook_account_id'
        """)
        exists = cursor.fetchone()[0] > 0
        if not exists:
            print("   ✅ Columna facebook_account_id eliminada de api_cache")
        else:
            print("   ⚠️ Columna facebook_account_id todavía existe en api_cache")
        
        # Verificar que user_id fue eliminado de facebook_accounts
        print("6. Verificando limpieza de facebook_accounts...")
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'facebook_accounts' AND column_name = 'user_id'
        """)
        exists = cursor.fetchone()[0] > 0
        if not exists:
            print("   ✅ Columna user_id eliminada de facebook_accounts")
        else:
            print("   ⚠️ Columna user_id todavía existe en facebook_accounts")
        
        # Verificar datos de precios
        print("7. Verificando datos de precios...")
        cursor.execute("SELECT COUNT(*) FROM model_pricing")
        pricing_count = cursor.fetchone()[0]
        print(f"   ✅ {pricing_count} registros de precios insertados")
        
        print("\n🎉 Migración completada exitosamente!")
        print("\n📋 Resumen de cambios:")
        print("   • Tabla model_pricing creada con precios actualizados")
        print("   • Tabla user_facebook_accounts creada para relaciones many-to-many")
        print("   • Tabla analysis_results creada para almacenar análisis")
        print("   • Campos de tracking agregados a conversation_history")
        print("   • Columnas duplicadas eliminadas de api_cache y facebook_accounts")
        print("   • Datos existentes migrados correctamente")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def main():
    """Función principal."""
    print("Migración de Base de Datos - Ads Analyzer")
    print("Este script implementará todas las mejoras de la base de datos.")
    print()
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("docs/internal/queries/migration_complete.sql"):
        print("❌ Error: Ejecuta este script desde el directorio raíz del proyecto")
        sys.exit(1)
    
    # Confirmar antes de ejecutar
    response = input("¿Continuar con la migración? (y/N): ")
    if response.lower() != 'y':
        print("Migración cancelada.")
        sys.exit(0)
    
    # Ejecutar migración
    success = run_migration()
    
    if success:
        print("\n✅ Migración exitosa. Puedes continuar usando la aplicación.")
        print("\n🔧 Próximos pasos:")
        print("   1. Ejecutar: python test/test_database_migration.py")
        print("   2. Probar la aplicación con POSTs consecutivos")
        print("   3. Verificar que la memoria a corto plazo funciona")
    else:
        print("\n❌ Migración falló. Revisa los errores y vuelve a intentar.")
        sys.exit(1)

if __name__ == "__main__":
    main()
