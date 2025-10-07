#!/usr/bin/env python3
"""
Script de prueba para verificar la migración de base de datos y nuevas funcionalidades.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db
from src.models import (
    User, FacebookAccount, UserFacebookAccount, ModelPricing, 
    AnalysisResult, ConversationHistory
)
from src.utils.cost_calculator import CostCalculator

def test_database_migration():
    """Prueba que todas las nuevas tablas y funcionalidades estén funcionando."""
    
    print("🧪 Probando Migración de Base de Datos")
    print("=" * 50)
    
    try:
        # Test 1: Verificar que las nuevas tablas existen
        print("1. Verificando nuevas tablas...")
        db_gen = get_db()
        db = next(db_gen)
        
        # Verificar ModelPricing
        pricing_count = db.query(ModelPricing).count()
        print(f"   ✅ ModelPricing: {pricing_count} registros")
        
        # Verificar UserFacebookAccount
        user_fb_count = db.query(UserFacebookAccount).count()
        print(f"   ✅ UserFacebookAccount: {user_fb_count} registros")
        
        # Verificar AnalysisResult
        analysis_count = db.query(AnalysisResult).count()
        print(f"   ✅ AnalysisResult: {analysis_count} registros")
        
        # Test 2: Verificar campos nuevos en ConversationHistory
        print("2. Verificando campos nuevos en ConversationHistory...")
        conv_count = db.query(ConversationHistory).count()
        print(f"   ✅ ConversationHistory: {conv_count} registros")
        
        # Verificar que los nuevos campos existen (intentando acceder a ellos)
        try:
            sample_conv = db.query(ConversationHistory).first()
            if sample_conv:
                # Estos campos deberían existir ahora
                _ = sample_conv.full_prompt_sent
                _ = sample_conv.llm_params
                _ = sample_conv.tokens_used
                _ = sample_conv.estimated_cost_usd
                print("   ✅ Nuevos campos en ConversationHistory: OK")
            else:
                print("   ⚠️ No hay registros en ConversationHistory para probar")
        except AttributeError as e:
            print(f"   ❌ Error en nuevos campos: {e}")
            return False
        
        # Test 3: Probar CostCalculator
        print("3. Probando CostCalculator...")
        
        # Probar obtención de precios
        pricing = CostCalculator.get_model_pricing('gpt-4-turbo')
        if pricing:
            print(f"   ✅ Precios obtenidos: ${pricing['input_cost_per_1k_tokens']} input, ${pricing['output_cost_per_1k_tokens']} output")
        else:
            print("   ⚠️ No se encontraron precios para gpt-4-turbo")
        
        # Probar cálculo de costos
        cost = CostCalculator.calculate_cost(1000, 500, 'gpt-4-turbo')
        if cost:
            print(f"   ✅ Cálculo de costo: ${cost:.6f} para 1000 input + 500 output tokens")
        else:
            print("   ⚠️ No se pudo calcular el costo")
        
        # Probar estimación de tokens
        tokens = CostCalculator.estimate_tokens_from_text("Hello, this is a test message.")
        print(f"   ✅ Estimación de tokens: {tokens} tokens para texto de prueba")
        
        # Test 4: Verificar relaciones many-to-many
        print("4. Probando relaciones many-to-many...")
        
        # Obtener un usuario
        user = db.query(User).first()
        if user:
            print(f"   ✅ Usuario encontrado: {user.name} ({user.email})")
            
            # Verificar cuentas asignadas
            assigned_accounts = db.query(FacebookAccount).join(
                UserFacebookAccount, 
                FacebookAccount.id == UserFacebookAccount.facebook_account_id
            ).filter(
                UserFacebookAccount.user_id == user.id
            ).all()
            
            print(f"   ✅ Cuentas asignadas al usuario: {len(assigned_accounts)}")
            for account in assigned_accounts:
                print(f"      - {account.account_name} ({account.ad_account_id})")
        else:
            print("   ⚠️ No se encontraron usuarios")
        
        # Test 5: Verificar que facebook_accounts ya no tiene user_id
        print("5. Verificando limpieza de facebook_accounts...")
        try:
            # Intentar acceder a user_id (debería fallar)
            sample_account = db.query(FacebookAccount).first()
            if sample_account:
                _ = sample_account.user_id  # Esto debería fallar
                print("   ❌ ERROR: user_id todavía existe en facebook_accounts")
                return False
        except AttributeError:
            print("   ✅ user_id eliminado correctamente de facebook_accounts")
        
        print("\n🎉 Todas las pruebas de migración pasaron correctamente!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'db' in locals():
            db.close()

def test_cost_calculation():
    """Prueba específica del cálculo de costos."""
    
    print("\n💰 Probando Cálculo de Costos")
    print("=" * 30)
    
    # Test con diferentes modelos
    models_to_test = ['gpt-4-turbo', 'gpt-35-turbo', 'default']
    
    for model in models_to_test:
        print(f"\nProbando modelo: {model}")
        
        # Obtener precios
        pricing = CostCalculator.get_model_pricing(model)
        if pricing:
            print(f"  Precios: ${pricing['input_cost_per_1k_tokens']} input, ${pricing['output_cost_per_1k_tokens']} output")
            
            # Calcular costo para diferentes cantidades de tokens
            test_cases = [
                (100, 50),    # Conversación corta
                (1000, 500),  # Conversación media
                (5000, 2000), # Conversación larga
            ]
            
            for input_tokens, output_tokens in test_cases:
                cost = CostCalculator.calculate_cost(input_tokens, output_tokens, model)
                if cost:
                    print(f"  {input_tokens} input + {output_tokens} output = ${cost:.6f}")
                else:
                    print(f"  Error calculando costo para {input_tokens}+{output_tokens}")
        else:
            print(f"  No se encontraron precios para {model}")

if __name__ == "__main__":
    success = test_database_migration()
    test_cost_calculation()
    sys.exit(0 if success else 1)
