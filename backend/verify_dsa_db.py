#!/usr/bin/env python
"""
Script para verificar la conexión a la base de datos con manejo de encoding.
"""
import os
import sys

# Configurar encoding antes de cualquier cosa
if sys.platform == 'win32':
    import locale
    locale.setlocale(locale.LC_ALL, 'C')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dahell_backend.settings')

try:
    import django
    django.setup()
    
    from core.models import DomainReputation, MarketAnalysisReport, UniqueProductCluster
    
    print("=" * 60)
    print("✅ Conexión a Base de Datos Exitosa")
    print("=" * 60)
    
    # Verificar conteos
    domain_count = DomainReputation.objects.count()
    report_count = MarketAnalysisReport.objects.count()
    cluster_count = UniqueProductCluster.objects.count()
    
    print(f"\n📊 Estadísticas de Tablas DSA:")
    print(f"   - DomainReputation: {domain_count} registros")
    print(f"   - MarketAnalysisReport: {report_count} registros")
    print(f"   - UniqueProductCluster: {cluster_count} registros")
    
    # Verificar si hay reportes SYNTHESIZED
    synthesized_reports = MarketAnalysisReport.objects.filter(market_state="SYNTHESIZED").count()
    discovered_reports = MarketAnalysisReport.objects.filter(market_state="DISCOVERED").count()
    
    print(f"\n📈 Estados de Reportes:")
    print(f"   - SYNTHESIZED (pendientes discovery): {synthesized_reports}")
    print(f"   - DISCOVERED (completados): {discovered_reports}")
    
    print("\n" + "=" * 60)
    print("✅ Verificación Completada - [DSA-01] FUNCIONANDO")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
