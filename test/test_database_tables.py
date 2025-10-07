#!/usr/bin/env python3
"""
Script de prueba para verificar que las tablas estén correctamente creadas en la base de datos.
Valida el esquema, relaciones, índices y datos de ejemplo.
"""

import sys
import os
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import engine, SessionLocal, test_connection
from src.models import (
    User, FacebookAccount, UserFacebookAccount, ApiCache, 
    ConversationHistory, PromptVersion, CampaignPerformanceData, 
    ModelPricing, AnalysisResult
)

def test_database_connection():
    """Prueba la conexión a la base de datos"""
    print("🔌 Probando conexión a la base de datos...")
    
    if test_connection():
        print("✅ Conexión exitosa a la base de datos")
        return True
    else:
        print("❌ Error de conexión a la base de datos")
        return False

def test_tables_exist():
    """Verifica que todas las tablas existan en la base de datos"""
    print("\n📋 Verificando existencia de tablas...")
    
    expected_tables = [
        'users', 'facebook_accounts', 'user_facebook_accounts', 
        'api_cache', 'conversation_history', 'prompt_versions',
        'campaign_performance_data', 'model_pricing', 'analysis_results'
    ]
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    missing_tables = []
    for table in expected_tables:
        if table in existing_tables:
            print(f"✅ Tabla '{table}' existe")
        else:
            print(f"❌ Tabla '{table}' NO existe")
            missing_tables.append(table)
    
    if missing_tables:
        print(f"\n⚠️  Tablas faltantes: {missing_tables}")
        return False
    else:
        print("\n✅ Todas las tablas existen")
        return True

def test_table_columns():
    """Verifica que las columnas de cada tabla estén correctas"""
    print("\n🔍 Verificando columnas de las tablas...")
    
    inspector = inspect(engine)
    
    # Definir las columnas esperadas para cada tabla
    expected_columns = {
        'users': ['id', 'email', 'name', 'password', 'is_active', 'created_at', 'updated_at'],
        'facebook_accounts': ['id', 'ad_account_id', 'account_name', 'key_vault_secret_name', 'created_at'],
        'user_facebook_accounts': ['id', 'user_id', 'facebook_account_id', 'assigned_at', 'assigned_by', 'is_active', 'notes'],
        'api_cache': ['id', 'ad_account_id', 'date_period', 'query_hash', 'result_json', 'created_at'],
        'conversation_history': ['id', 'session_id', 'user_id', 'user_prompt', 'full_prompt_sent', 'llm_response', 'llm_params', 'tokens_used', 'estimated_cost_usd', 'timestamp'],
        'prompt_versions': ['id', 'prompt_name', 'version', 'prompt_text', 'is_active', 'created_at'],
        'campaign_performance_data': ['id', 'ad_account_id', 'campaign_id', 'campaign_name', 'date', 'metrics', 'facebook_account_id', 'created_at'],
        'model_pricing': ['id', 'model_name', 'input_cost_per_1k_tokens', 'output_cost_per_1k_tokens', 'effective_date', 'created_at', 'updated_at'],
        'analysis_results': ['id', 'user_id', 'session_id', 'analysis_type', 'facebook_account_id', 'result_text', 'analysis_metadata', 'created_at']
    }
    
    all_columns_correct = True
    
    for table_name, expected_cols in expected_columns.items():
        try:
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            missing_cols = set(expected_cols) - set(columns)
            extra_cols = set(columns) - set(expected_cols)
            
            if missing_cols or extra_cols:
                print(f"❌ Tabla '{table_name}':")
                if missing_cols:
                    print(f"   - Columnas faltantes: {missing_cols}")
                if extra_cols:
                    print(f"   - Columnas extra: {extra_cols}")
                all_columns_correct = False
            else:
                print(f"✅ Tabla '{table_name}': columnas correctas")
                
        except Exception as e:
            print(f"❌ Error verificando tabla '{table_name}': {e}")
            all_columns_correct = False
    
    return all_columns_correct

def test_indexes():
    """Verifica que los índices estén creados correctamente"""
    print("\n📊 Verificando índices...")
    
    db = SessionLocal()
    try:
        # Consulta para obtener todos los índices
        result = db.execute(text("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes 
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """))
        
        indexes = result.fetchall()
        
        # Índices esperados (principales)
        expected_indexes = [
            'idx_users_email', 'idx_users_active',
            'idx_facebook_accounts_ad_account_id',
            'idx_user_facebook_accounts_user_id', 'idx_user_facebook_accounts_facebook_id',
            'idx_api_cache_account_period', 'idx_api_cache_hash',
            'idx_conversation_user_session', 'idx_conversation_timestamp',
            'idx_prompt_name_version', 'idx_prompt_active',
            'idx_campaign_account_date', 'idx_campaign_id_date',
            'idx_model_pricing_model_date',
            'idx_analysis_results_user_id', 'idx_analysis_results_type'
        ]
        
        existing_index_names = [idx.indexname for idx in indexes]
        missing_indexes = set(expected_indexes) - set(existing_index_names)
        
        if missing_indexes:
            print(f"⚠️  Índices faltantes: {missing_indexes}")
            print(f"✅ Índices existentes: {len(existing_index_names)}")
            return False
        else:
            print(f"✅ Todos los índices principales existen ({len(existing_index_names)} total)")
            return True
            
    except Exception as e:
        print(f"❌ Error verificando índices: {e}")
        return False
    finally:
        db.close()

def test_foreign_keys():
    """Verifica que las claves foráneas estén configuradas correctamente"""
    print("\n🔗 Verificando claves foráneas...")
    
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT 
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.column_name
        """))
        
        foreign_keys = result.fetchall()
        
        # Claves foráneas esperadas
        expected_fks = [
            ('user_facebook_accounts', 'user_id', 'users', 'id'),
            ('user_facebook_accounts', 'facebook_account_id', 'facebook_accounts', 'id'),
            ('conversation_history', 'user_id', 'users', 'id'),
            ('analysis_results', 'user_id', 'users', 'id'),
            ('analysis_results', 'facebook_account_id', 'facebook_accounts', 'id'),
            ('campaign_performance_data', 'facebook_account_id', 'facebook_accounts', 'id')
        ]
        
        existing_fks = [(fk.table_name, fk.column_name, fk.foreign_table_name, fk.foreign_column_name) 
                       for fk in foreign_keys]
        
        missing_fks = set(expected_fks) - set(existing_fks)
        
        if missing_fks:
            print(f"⚠️  Claves foráneas faltantes: {missing_fks}")
            return False
        else:
            print(f"✅ Todas las claves foráneas están configuradas ({len(existing_fks)} total)")
            return True
            
    except Exception as e:
        print(f"❌ Error verificando claves foráneas: {e}")
        return False
    finally:
        db.close()

def test_sample_data():
    """Verifica que los datos de ejemplo estén insertados"""
    print("\n📝 Verificando datos de ejemplo...")
    
    db = SessionLocal()
    try:
        # Verificar usuarios de ejemplo
        user_count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        print(f"✅ Usuarios en la base de datos: {user_count}")
        
        # Verificar cuentas de Facebook
        fb_account_count = db.execute(text("SELECT COUNT(*) FROM facebook_accounts")).scalar()
        print(f"✅ Cuentas de Facebook: {fb_account_count}")
        
        # Verificar precios de modelos
        pricing_count = db.execute(text("SELECT COUNT(*) FROM model_pricing")).scalar()
        print(f"✅ Precios de modelos: {pricing_count}")
        
        # Verificar prompts
        prompt_count = db.execute(text("SELECT COUNT(*) FROM prompt_versions")).scalar()
        print(f"✅ Versiones de prompts: {prompt_count}")
        
        # Verificar asignaciones usuario-cuenta
        assignment_count = db.execute(text("SELECT COUNT(*) FROM user_facebook_accounts")).scalar()
        print(f"✅ Asignaciones usuario-cuenta: {assignment_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando datos de ejemplo: {e}")
        return False
    finally:
        db.close()

def test_sqlalchemy_models():
    """Prueba que los modelos SQLAlchemy funcionen correctamente"""
    print("\n🐍 Probando modelos SQLAlchemy...")
    
    db = SessionLocal()
    try:
        # Probar crear un usuario (con email único)
        import time
        test_email = f"test_{int(time.time())}@example.com"
        test_user = User(
            email=test_email,
            name="Usuario de Prueba",
            is_active=True
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"✅ Usuario creado con ID: {test_user.id}")
        
        # Probar crear una cuenta de Facebook (con ID único)
        test_ad_account_id = f"act_test{int(time.time())}"
        test_fb_account = FacebookAccount(
            ad_account_id=test_ad_account_id,
            account_name="Cuenta de Prueba",
            key_vault_secret_name=f"test-secret-{int(time.time())}"
        )
        db.add(test_fb_account)
        db.commit()
        db.refresh(test_fb_account)
        print(f"✅ Cuenta de Facebook creada con ID: {test_fb_account.id}")
        
        # Probar crear una asignación
        test_assignment = UserFacebookAccount(
            user_id=test_user.id,
            facebook_account_id=test_fb_account.id,
            is_active=True
        )
        db.add(test_assignment)
        db.commit()
        print("✅ Asignación usuario-cuenta creada")
        
        # Limpiar datos de prueba
        db.delete(test_assignment)
        db.delete(test_fb_account)
        db.delete(test_user)
        db.commit()
        print("✅ Datos de prueba eliminados")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando modelos SQLAlchemy: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def run_comprehensive_test():
    """Ejecuta todas las pruebas de manera integral"""
    print("🚀 INICIANDO PRUEBAS COMPLETAS DE BASE DE DATOS")
    print("=" * 60)
    
    tests = [
        ("Conexión a BD", test_database_connection),
        ("Existencia de tablas", test_tables_exist),
        ("Columnas de tablas", test_table_columns),
        ("Índices", test_indexes),
        ("Claves foráneas", test_foreign_keys),
        ("Datos de ejemplo", test_sample_data),
        ("Modelos SQLAlchemy", test_sqlalchemy_models)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error en prueba '{test_name}': {e}")
            results.append((test_name, False))
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Resultado final: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! La base de datos está correctamente configurada.")
        return True
    else:
        print("⚠️  Algunas pruebas fallaron. Revisa los errores anteriores.")
        return False

if __name__ == "__main__":
    try:
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Pruebas interrumpidas por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        sys.exit(1)
