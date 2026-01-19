#!/usr/bin/env python3
"""
Script de Auditoría Completa del Classifier
Genera un reporte detallado de todos los resultados del classifier
"""

import os
import sys
import django
import json
from datetime import datetime, timedelta
from pathlib import Path

# Setup Django
sys.path.insert(0, '/app/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dahell_backend.settings')
django.setup()

from django.db import connection
from core.models import Product, ProductEmbedding, Category, ProductCategory, ProductClusterMembership, UniqueProductCluster, AIFeedback

def execute_query(query, description=""):
    """Ejecuta una query y retorna los resultados"""
    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description] if cursor.description else []
        results = cursor.fetchall()
        return {
            'description': description,
            'columns': columns,
            'rows': results,
            'row_count': len(results)
        }

def main():
    print("=" * 80)
    print("AUDITORÍA COMPLETA DEL CLASSIFIER")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'sections': {}
    }
    
    # =====================================================
    # PARTE 1: ESTADÍSTICAS GENERALES
    # =====================================================
    print("\n📊 PARTE 1: ESTADÍSTICAS GENERALES")
    print("-" * 80)
    
    total_products = Product.objects.count()
    classified_products = Product.objects.filter(taxonomy_concept__isnull=False).exclude(taxonomy_concept='').count()
    unclassified_products = total_products - classified_products
    classification_rate = (classified_products / total_products * 100) if total_products > 0 else 0
    
    stats = {
        'total_products': total_products,
        'classified_products': classified_products,
        'unclassified_products': unclassified_products,
        'classification_rate': round(classification_rate, 2)
    }
    
    print(f"Total de Productos: {total_products:,}")
    print(f"Productos Clasificados: {classified_products:,}")
    print(f"Productos Sin Clasificar: {unclassified_products:,}")
    print(f"Tasa de Clasificación: {classification_rate:.2f}%")
    
    report['sections']['general_stats'] = stats
    
    # =====================================================
    # PARTE 2: TOP CONCEPTOS
    # =====================================================
    print("\n🏷️  PARTE 2: TOP 50 CONCEPTOS MÁS FRECUENTES")
    print("-" * 80)
    
    top_concepts_query = """
        SELECT 
            taxonomy_concept,
            COUNT(*) as product_count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM products WHERE taxonomy_concept IS NOT NULL AND taxonomy_concept != ''), 2) as percentage
        FROM products
        WHERE taxonomy_concept IS NOT NULL AND taxonomy_concept != ''
        GROUP BY taxonomy_concept
        ORDER BY product_count DESC
        LIMIT 50
    """
    
    top_concepts_result = execute_query(top_concepts_query, "Top 50 Conceptos")
    top_concepts = []
    
    for row in top_concepts_result['rows']:
        concept, count, percentage = row
        print(f"{concept:50s} | {count:6,} productos ({percentage:5.2f}%)")
        top_concepts.append({
            'concept': concept,
            'product_count': count,
            'percentage': float(percentage)
        })
    
    report['sections']['top_concepts'] = top_concepts
    
    # =====================================================
    # PARTE 3: DISTRIBUCIÓN POR INDUSTRIA
    # =====================================================
    print("\n🏭 PARTE 3: DISTRIBUCIÓN POR INDUSTRIA")
    print("-" * 80)
    
    industries_query = """
        SELECT 
            taxonomy_industry,
            COUNT(*) as product_count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM products WHERE taxonomy_industry IS NOT NULL AND taxonomy_industry != ''), 2) as percentage
        FROM products
        WHERE taxonomy_industry IS NOT NULL AND taxonomy_industry != ''
        GROUP BY taxonomy_industry
        ORDER BY product_count DESC
    """
    
    industries_result = execute_query(industries_query, "Distribución por Industria")
    industries = []
    
    for row in industries_result['rows']:
        industry, count, percentage = row
        print(f"{industry:50s} | {count:6,} productos ({percentage:5.2f}%)")
        industries.append({
            'industry': industry,
            'product_count': count,
            'percentage': float(percentage)
        })
    
    report['sections']['industries'] = industries
    
    # =====================================================
    # PARTE 4: ANÁLISIS DE CALIDAD
    # =====================================================
    print("\n✅ PARTE 4: ANÁLISIS DE CALIDAD DE CLASIFICACIÓN")
    print("-" * 80)
    
    quality_query = """
        SELECT 
            COUNT(DISTINCT CASE WHEN p.taxonomy_concept IS NOT NULL AND p.taxonomy_concept != '' 
                AND pe.product_id IS NOT NULL THEN CONCAT(p.product_id, '-', p.supplier_id) END) as with_vector_and_concept,
            COUNT(DISTINCT CASE WHEN (p.taxonomy_concept IS NULL OR p.taxonomy_concept = '') 
                AND pe.product_id IS NOT NULL THEN CONCAT(p.product_id, '-', p.supplier_id) END) as with_vector_no_concept,
            COUNT(DISTINCT CASE WHEN pe.product_id IS NULL THEN CONCAT(p.product_id, '-', p.supplier_id) END) as without_vector
        FROM products p
        LEFT JOIN product_embeddings pe ON p.product_id = pe.product_id
    """
    
    quality_result = execute_query(quality_query, "Análisis de Calidad")
    with_vector_and_concept, with_vector_no_concept, without_vector = quality_result['rows'][0]
    
    quality_stats = {
        'with_vector_and_concept': with_vector_and_concept,
        'with_vector_no_concept': with_vector_no_concept,
        'without_vector': without_vector
    }
    
    print(f"Productos con Vector Y Concepto: {with_vector_and_concept:,}")
    print(f"Productos con Vector SIN Concepto: {with_vector_no_concept:,}")
    print(f"Productos SIN Vector: {without_vector:,}")
    
    report['sections']['quality_stats'] = quality_stats
    
    # =====================================================
    # PARTE 5: ANÁLISIS TEMPORAL (Últimos 7 días)
    # =====================================================
    print("\n📅 PARTE 5: PRODUCTOS CLASIFICADOS POR DÍA (Últimos 7 días)")
    print("-" * 80)
    
    temporal_query = """
        SELECT 
            DATE(updated_at) as date,
            COUNT(*) as products_classified
        FROM products
        WHERE taxonomy_concept IS NOT NULL 
          AND taxonomy_concept != ''
          AND updated_at >= NOW() - INTERVAL '7 days'
        GROUP BY DATE(updated_at)
        ORDER BY date DESC
    """
    
    temporal_result = execute_query(temporal_query, "Clasificación por Día")
    temporal_data = []
    
    for row in temporal_result['rows']:
        date, count = row
        print(f"{date} | {count:6,} productos")
        temporal_data.append({
            'date': str(date),
            'products_classified': count
        })
    
    report['sections']['temporal_analysis'] = temporal_data
    
    # =====================================================
    # PARTE 6: CONCEPTOS ÚNICOS (Posibles errores)
    # =====================================================
    print("\n⚠️  PARTE 6: CONCEPTOS CON UN SOLO PRODUCTO (Posibles errores)")
    print("-" * 80)
    
    unique_concepts_query = """
        SELECT 
            taxonomy_concept,
            COUNT(*) as product_count
        FROM products
        WHERE taxonomy_concept IS NOT NULL AND taxonomy_concept != ''
        GROUP BY taxonomy_concept
        HAVING COUNT(*) = 1
        ORDER BY taxonomy_concept
        LIMIT 50
    """
    
    unique_concepts_result = execute_query(unique_concepts_query, "Conceptos Únicos")
    unique_concepts = []
    
    print(f"Total de conceptos únicos: {unique_concepts_result['row_count']}")
    for i, row in enumerate(unique_concepts_result['rows'][:20], 1):
        concept, count = row
        print(f"{i:3d}. {concept}")
        unique_concepts.append(concept)
    
    if unique_concepts_result['row_count'] > 20:
        print(f"... y {unique_concepts_result['row_count'] - 20} más")
    
    report['sections']['unique_concepts'] = {
        'total': unique_concepts_result['row_count'],
        'sample': unique_concepts[:20]
    }
    
    # =====================================================
    # PARTE 7: MUESTRA DE PRODUCTOS CLASIFICADOS
    # =====================================================
    print("\n📦 PARTE 7: MUESTRA DE PRODUCTOS CLASIFICADOS RECIENTEMENTE")
    print("-" * 80)
    
    sample_query = """
        SELECT 
            p.product_id,
            p.supplier_id,
            p.title,
            p.taxonomy_concept,
            p.taxonomy_industry,
            p.sale_price,
            p.updated_at,
            (SELECT COUNT(*) FROM product_embeddings pe WHERE pe.product_id = p.product_id) as has_vector
        FROM products p
        WHERE p.taxonomy_concept IS NOT NULL AND p.taxonomy_concept != ''
        ORDER BY p.updated_at DESC
        LIMIT 20
    """
    
    sample_result = execute_query(sample_query, "Muestra de Productos")
    sample_products = []
    
    for row in sample_result['rows']:
        product_id, supplier_id, title, concept, industry, price, updated_at, has_vector = row
        print(f"\nProduct ID: {product_id} | Supplier ID: {supplier_id}")
        print(f"  Título: {title[:70]}...")
        print(f"  Concepto: {concept}")
        print(f"  Industria: {industry}")
        print(f"  Precio: ${price}")
        print(f"  Vector: {'✓' if has_vector else '✗'}")
        print(f"  Actualizado: {updated_at}")
        
        sample_products.append({
            'product_id': product_id,
            'supplier_id': supplier_id,
            'title': title,
            'taxonomy_concept': concept,
            'taxonomy_industry': industry,
            'price': float(price) if price else None,
            'updated_at': str(updated_at),
            'has_vector': bool(has_vector)
        })
    
    report['sections']['sample_products'] = sample_products
    
    # =====================================================
    # PARTE 8: AI FEEDBACK
    # =====================================================
    print("\n🤖 PARTE 8: ANÁLISIS DE AI FEEDBACK")
    print("-" * 80)
    
    ai_feedback_count = AIFeedback.objects.count()
    print(f"Total de entradas en AI Feedback: {ai_feedback_count:,}")
    
    if ai_feedback_count > 0:
        latest_feedback = AIFeedback.objects.order_by('-created_at')[:10]
        print("\nÚltimas 10 entradas:")
        for fb in latest_feedback:
            print(f"  - {fb.created_at}: {fb.feedback_type if hasattr(fb, 'feedback_type') else 'N/A'}")
    
    report['sections']['ai_feedback'] = {
        'total_entries': ai_feedback_count
    }
    
    # =====================================================
    # PARTE 9: CREAR BACKUPS
    # =====================================================
    print("\n💾 PARTE 9: CREANDO BACKUPS DE TABLAS")
    print("-" * 80)
    
    backup_queries = [
        """
        DROP TABLE IF EXISTS audit_products_classifier_backup;
        CREATE TABLE audit_products_classifier_backup AS
        SELECT 
            p.*,
            (SELECT COUNT(*) FROM product_embeddings pe WHERE pe.product_id = p.product_id) as has_vector,
            (SELECT COUNT(*) FROM product_categories pc WHERE pc.product_id = p.product_id AND pc.supplier_id = p.supplier_id) as category_count
        FROM products p
        WHERE p.taxonomy_concept IS NOT NULL AND p.taxonomy_concept != '';
        """,
        """
        DROP TABLE IF EXISTS audit_embeddings_classifier_backup;
        CREATE TABLE audit_embeddings_classifier_backup AS
        SELECT pe.*
        FROM product_embeddings pe
        INNER JOIN products p ON pe.product_id = p.product_id
        WHERE p.taxonomy_concept IS NOT NULL AND p.taxonomy_concept != '';
        """,
        """
        DROP TABLE IF EXISTS audit_categories_classifier_backup;
        CREATE TABLE audit_categories_classifier_backup AS
        SELECT pc.*
        FROM product_categories pc
        INNER JOIN products p ON pc.product_id = p.product_id AND pc.supplier_id = p.supplier_id
        WHERE p.taxonomy_concept IS NOT NULL AND p.taxonomy_concept != '';
        """,
        """
        DROP TABLE IF EXISTS audit_clusters_classifier_backup;
        CREATE TABLE audit_clusters_classifier_backup AS
        SELECT pcm.*
        FROM product_cluster_membership pcm
        INNER JOIN products p ON pcm.product_id = p.product_id AND pcm.supplier_id = p.supplier_id
        WHERE p.taxonomy_concept IS NOT NULL AND p.taxonomy_concept != '';
        """
    ]
    
    backup_tables = [
        'audit_products_classifier_backup',
        'audit_embeddings_classifier_backup',
        'audit_categories_classifier_backup',
        'audit_clusters_classifier_backup'
    ]
    
    with connection.cursor() as cursor:
        for query in backup_queries:
            try:
                cursor.execute(query)
                print("✓ Backup creado exitosamente")
            except Exception as e:
                print(f"✗ Error creando backup: {e}")
    
    # Verificar backups
    print("\n📊 Verificando backups:")
    backup_stats = {}
    for table in backup_tables:
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count:,} registros")
                backup_stats[table] = count
        except Exception as e:
            print(f"  {table}: Error - {e}")
            backup_stats[table] = 0
    
    report['sections']['backups'] = backup_stats
    
    # =====================================================
    # GUARDAR REPORTE JSON
    # =====================================================
    print("\n💾 GUARDANDO REPORTE JSON")
    print("-" * 80)
    
    report_path = Path('/app/classifier_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✓ Reporte guardado en: {report_path}")
    
    # =====================================================
    # RESUMEN FINAL
    # =====================================================
    print("\n" + "=" * 80)
    print("📋 RESUMEN EJECUTIVO")
    print("=" * 80)
    print(f"\n✓ Total de Productos: {total_products:,}")
    print(f"✓ Productos Clasificados: {classified_products:,} ({classification_rate:.2f}%)")
    print(f"✓ Conceptos Únicos Generados: {len(top_concepts)}")
    print(f"✓ Industrias Identificadas: {len(industries)}")
    print(f"✓ Productos con Vector y Concepto: {with_vector_and_concept:,}")
    print(f"✓ Backups Creados: {len([v for v in backup_stats.values() if v > 0])}/{len(backup_tables)}")
    print(f"\n✓ Reporte completo guardado en: classifier_report.json")
    print("\n" + "=" * 80)
    print("AUDITORÍA COMPLETADA")
    print("=" * 80)

if __name__ == '__main__':
    main()
