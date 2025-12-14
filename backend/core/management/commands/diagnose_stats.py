from django.core.management.base import BaseCommand
from core.models import Product, UniqueProductCluster, ProductClusterMembership, Supplier, Warehouse, ProductEmbedding
import pathlib
import os

class Command(BaseCommand):
    help = 'Run stats diagnostics on the database'

    def handle(self, *args, **kwargs):
        self.stdout.write("--- DIAGNOSTICO DEL SISTEMA DAHELL ---")
        
        # 1. Analisis de Archivos RAW
        self.stdout.write("\n1. SISTEMA DE ARCHIVOS (Raw Data)")
        raw_dir = pathlib.Path("raw_data")
        total_lines = 0
        if raw_dir.exists():
            files = list(raw_dir.glob("*.jsonl"))
            self.stdout.write(f"   Archivos encontrados: {len(files)}")
            for f in files:
                try:
                    size_mb = f.stat().st_size / (1024 * 1024)
                    with open(f, 'rb') as fp:
                        lines = sum(1 for _ in fp)
                    total_lines += lines
                    self.stdout.write(f"   - {f.name}: {size_mb:.2f} MB ({lines} registros)")
                except Exception as e:
                    self.stdout.write(f"   - {f.name}: Error leyendo ({e})")
        else:
             self.stdout.write("   ⚠️ No existe directorio raw_data/")
        
        self.stdout.write(f"   > Total registros extraídos: {total_lines}")

        # 2. Base de Datos
        self.stdout.write("\n2. BASE DE DATOS (Conteos)")
        try:
            total_products = Product.objects.count()
            self.stdout.write(f"   - Productos: {total_products}")
            
            total_suppliers = Supplier.objects.count()
            self.stdout.write(f"   - Proveedores: {total_suppliers}")
            
            total_warehouses = Warehouse.objects.count()
            self.stdout.write(f"   - Bodegas: {total_warehouses}")
            
            total_vectors = ProductEmbedding.objects.count()
            valid_vectors = ProductEmbedding.objects.filter(embedding_visual__isnull=False).count()
            self.stdout.write(f"   - Vectores (IA): {valid_vectors} válidos / {total_vectors} total")
            
        except Exception as e:
            self.stdout.write(f"   ❌ Error conectando a DB: {e}")
            return

        # 3. Clustering Stats
        self.stdout.write("\n3. CLUSTERING")
        total_clusters = UniqueProductCluster.objects.count()
        self.stdout.write(f"   - Clusters Totales: {total_clusters}")

        if total_products > 0:
            clustered_products = ProductClusterMembership.objects.values('product').distinct().count()
            coverage = (clustered_products / total_products * 100) if total_products > 0 else 0
            self.stdout.write(f"   - Productos Clusterizados: {clustered_products} (Cobertura: {coverage:.1f}%)")
        
        # 4. Insights
        self.stdout.write("\n4. INSIGHTS DE NEGOCIO")
        low_comp = UniqueProductCluster.objects.filter(total_competitors__lte=3).count()
        self.stdout.write(f"   - Oportunidades Baja Competencia (<=3): {low_comp}")
        
        high_margin = UniqueProductCluster.objects.filter(
            representative_product__profit_margin__gte=20000
        ).count()
        self.stdout.write(f"   - Oportunidades Alto Margen (>=20k): {high_margin}")
        
        gold = UniqueProductCluster.objects.filter(
            total_competitors__lte=3,
            representative_product__profit_margin__gte=20000
        ).count()
        self.stdout.write(f"   - 💎 MINAS DE ORO (Ambos): {gold}")

        self.stdout.write("\n✅ Diagnóstico finalizado.")

