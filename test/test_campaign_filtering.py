#!/usr/bin/env python3
"""
Script para probar la lógica de filtrado de campañas.
Útil para debugging de problemas de detección de tipos de campaña.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.facebook_tools import _filter_campaigns_by_type

def test_campaign_filtering():
    """Probar la lógica de filtrado de campañas"""
    print("🧪 Probando lógica de filtrado de campañas...")
    
    # Datos de prueba simulando campañas reales
    test_campaigns = [
        {
            'name': 'Canquén 5 _Lead Form',
            'id': '123456789',
            'objective': 'LEAD_GENERATION'
        },
        {
            'name': 'Vicuña 6633_Lead Form',
            'id': '987654321',
            'objective': 'LEAD_GENERATION'
        },
        {
            'name': 'Tráfico Web Q4',
            'id': '456789123',
            'objective': 'TRAFFIC'
        },
        {
            'name': 'Conversión E-commerce',
            'id': '789123456',
            'objective': 'CONVERSIONS'
        },
        {
            'Nombre de la campaña': 'Test Lead Form Campaign',  # Simulando DataFrame
            'Campaign ID': '111222333',
            'Objective': 'LEAD_GENERATION'
        }
    ]
    
    print(f"📊 Datos de prueba: {len(test_campaigns)} campañas")
    for i, campaign in enumerate(test_campaigns, 1):
        name = campaign.get('name', campaign.get('Nombre de la campaña', 'Sin nombre'))
        print(f"   {i}. {name}")
    
    print("\n🔍 Probando filtrado de campañas Lead Form...")
    
    # Probar filtrado
    filtered_campaigns = _filter_campaigns_by_type(test_campaigns, "lead_form")
    
    print(f"\n📋 Resultados:")
    print(f"   Total campañas: {len(test_campaigns)}")
    print(f"   Campañas Lead Form filtradas: {len(filtered_campaigns)}")
    
    if filtered_campaigns:
        print(f"\n✅ Campañas Lead Form encontradas:")
        for i, campaign in enumerate(filtered_campaigns, 1):
            name = campaign.get('name', campaign.get('Nombre de la campaña', 'Sin nombre'))
            print(f"   {i}. {name}")
    else:
        print(f"\n❌ No se encontraron campañas Lead Form")
    
    # Probar otros tipos
    print(f"\n🔍 Probando filtrado de campañas Traffic...")
    traffic_campaigns = _filter_campaigns_by_type(test_campaigns, "traffic")
    print(f"   Campañas Traffic filtradas: {len(traffic_campaigns)}")
    
    print(f"\n🔍 Probando filtrado de campañas Conversion...")
    conversion_campaigns = _filter_campaigns_by_type(test_campaigns, "conversion")
    print(f"   Campañas Conversion filtradas: {len(conversion_campaigns)}")
    
    return len(filtered_campaigns) > 0

def test_campaign_name_variations():
    """Probar diferentes variaciones de nombres de campañas Lead Form"""
    print("\n🧪 Probando variaciones de nombres Lead Form...")
    
    test_names = [
        "Campaña Lead Form",
        "Lead Form Campaign",
        "LEAD FORM TEST",
        "lead form prueba",
        "Campaña_Lead_Form",
        "LeadForm Campaign",
        "Lead-Form Test",
        "Campaña Tráfico",  # No debería coincidir
        "Conversión Test",  # No debería coincidir
    ]
    
    for name in test_names:
        campaign = {'name': name}
        filtered = _filter_campaigns_by_type([campaign], "lead_form")
        status = "✅" if filtered else "❌"
        print(f"   {status} '{name}' -> {len(filtered)} coincidencias")

def main():
    """Función principal"""
    print("🚀 Script de Prueba de Filtrado de Campañas")
    print("=" * 60)
    
    # Probar filtrado básico
    basic_test_ok = test_campaign_filtering()
    
    # Probar variaciones de nombres
    test_campaign_name_variations()
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📋 RESUMEN:")
    print(f"   Filtrado básico: {'✅ OK' if basic_test_ok else '❌ ERROR'}")
    
    if basic_test_ok:
        print("\n🎉 La lógica de filtrado funciona correctamente")
        sys.exit(0)
    else:
        print("\n⚠️  Hay problemas con la lógica de filtrado")
        sys.exit(1)

if __name__ == "__main__":
    main()
