#!/usr/bin/env python3
"""
Script de prueba para verificar el comportamiento de session IDs persistentes.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.agent_executor import DigitalMarketingAgent

def test_persistent_sessions():
    """Prueba que los session IDs sean persistentes para el mismo usuario."""
    
    print("🧪 Probando Session IDs Persistentes")
    print("=" * 50)
    
    # Crear agente para usuario 1
    print("1. Creando agente para usuario 1...")
    agent1 = DigitalMarketingAgent(user_id=1)
    session1 = agent1.session_id
    print(f"   Session ID: {session1}")
    
    # Crear otro agente para el mismo usuario
    print("2. Creando otro agente para usuario 1...")
    agent2 = DigitalMarketingAgent(user_id=1)
    session2 = agent2.session_id
    print(f"   Session ID: {session2}")
    
    # Verificar que sean iguales
    if session1 == session2:
        print("✅ PASS: Session IDs son persistentes para el mismo usuario")
    else:
        print("❌ FAIL: Session IDs no son persistentes")
        return False
    
    # Crear agente para usuario diferente
    print("3. Creando agente para usuario 2...")
    agent3 = DigitalMarketingAgent(user_id=2)
    session3 = agent3.session_id
    print(f"   Session ID: {session3}")
    
    # Verificar que sea diferente
    if session3 != session1:
        print("✅ PASS: Session IDs son diferentes para usuarios diferentes")
    else:
        print("❌ FAIL: Session IDs son iguales para usuarios diferentes")
        return False
    
    # Verificar formato de session ID
    expected_format = "persistent_1"
    if session1 == expected_format:
        print("✅ PASS: Formato de session ID correcto")
    else:
        print(f"❌ FAIL: Formato incorrecto. Esperado: {expected_format}, Obtenido: {session1}")
        return False
    
    print("\n🎉 Todas las pruebas pasaron correctamente!")
    return True

if __name__ == "__main__":
    success = test_persistent_sessions()
    sys.exit(0 if success else 1)
