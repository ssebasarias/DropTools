import sys
import os
import django
from django.conf import settings

# Manual Configuration
if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'dahell_db',
                'USER': 'dahell_admin',
                'PASSWORD': 'secure_password_123',
                'HOST': '127.0.0.1',
                'PORT': '5433',
            }
        },
        INSTALLED_APPS=[
            'core',
        ],
        TIME_ZONE='UTC',
        USE_TZ=True,
    )

django.setup()

from django.db.models import Count, Avg, Q
from core.models import Product, UniqueProductCluster, ProductClusterMembership, ProductEmbedding

def analyze():
    output = []
    output.append("--- 📊 SYSTEM STATUS REPORT 📊 ---")
    
    # 1. Product Counts
    total_products = Product.objects.count()
    classified_products = Product.objects.filter(taxonomy_concept__isnull=False).exclude(taxonomy_concept='').count()
    clustered_products = ProductClusterMembership.objects.count()
    embedded_products = ProductEmbedding.objects.filter(embedding_visual__isnull=False).count()
    
    output.append(f"\n1. 📈 PROGRESS METRICS:")
    output.append(f"   - Total Products in DB: {total_products}")
    output.append(f"   - Vectorized (Visual): {embedded_products} ({(embedded_products/total_products*100) if total_products else 0:.1f}%)")
    output.append(f"   - Classified (Taxonomy): {classified_products} ({(classified_products/total_products*100) if total_products else 0:.1f}%)")
    output.append(f"   - Clustered (Grouped): {clustered_products} ({(clustered_products/total_products*100) if total_products else 0:.1f}%)")

    # 2. Data Quality
    products_no_image = Product.objects.filter(Q(url_image_s3__isnull=True) | Q(url_image_s3='')).count()
    products_unknown_concept = Product.objects.filter(taxonomy_concept='UNKNOWN').count()
    
    output.append(f"\n2. 🧐 DATA QUALITY:")
    output.append(f"   - Products without Images: {products_no_image} ({(products_no_image/total_products*100) if total_products else 0:.1f}%)")
    output.append(f"   - Classified as 'UNKNOWN': {products_unknown_concept} ({(products_unknown_concept/classified_products*100) if classified_products else 0:.1f}%)")

    # 3. Concepts vs Products
    unique_concepts = Product.objects.exclude(taxonomy_concept__isnull=True).exclude(taxonomy_concept='').values('taxonomy_concept').distinct().count()
    
    output.append(f"\n3. 🧠 CONCEPTS VS PRODUCTS:")
    output.append(f"   - Unique Concepts Found: {unique_concepts}")
    if classified_products > 0 and unique_concepts > 0:
        output.append(f"   - Avg Products per Concept: {classified_products / unique_concepts:.1f}")
    
    # 4. Top Concepts
    output.append(f"\n4. 🏷️ TOP 10 CONCEPTS (By Volume):")
    top_concepts = Product.objects.exclude(taxonomy_concept__isnull=True).values('taxonomy_concept').annotate(count=Count('product_id')).order_by('-count')[:10]
    for c in top_concepts:
        concept_name = repr(c['taxonomy_concept'])
        count = c['count']
        output.append(f"   - {concept_name}: {count} products")

    # 5. Market Saturation
    total_clusters = UniqueProductCluster.objects.count()
    avg_competitors = UniqueProductCluster.objects.aggregate(avg=Avg('total_competitors'))['avg']
    
    output.append(f"\n5. 🏙️ MARKET SATURATION (CLUSTERS):")
    output.append(f"   - Total Unique Clusters (Distinct Items): {total_clusters}")
    output.append(f"   - Avg Competitors per Item: {avg_competitors:.2f}" if avg_competitors else "   - Avg Competitors per Item: N/A")
    
    # Most saturated clusters
    output.append("\n   🔥 TOP 5 MOST SATURATED CLUSTERS:")
    saturated_clusters = UniqueProductCluster.objects.order_by('-total_competitors')[:5]
    for cluster in saturated_clusters:
        name = cluster.concept_name
        if not name and cluster.representative_product:
            name = cluster.representative_product.taxonomy_concept
        
        output.append(f"   - Cluster {cluster.cluster_id} ({repr(name)}): {cluster.total_competitors} competitors")

    with open('analysis_report_direct.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    print("Report generated: analysis_report_direct.txt")

if __name__ == "__main__":
    analyze()
