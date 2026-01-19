
import os
import sys
import django
from django.db.models import Count, Avg, Q

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dahell_backend.settings')
django.setup()

from core.models import Product, UniqueProductCluster, ProductClusterMembership, ProductEmbedding

def analyze():
    print("--- 📊 SYSTEM STATUS REPORT (INTERNAL) 📊 ---")
    
    # 1. Product Counts
    total_products = Product.objects.count()
    classified_products = Product.objects.filter(taxonomy_concept__isnull=False).exclude(taxonomy_concept='').count()
    clustered_products = ProductClusterMembership.objects.count()
    embedded_products = ProductEmbedding.objects.filter(embedding_visual__isnull=False).count()
    
    print(f"\n1. 📈 PROGRESS METRICS:")
    print(f"   - Total Products in DB: {total_products}")
    print(f"   - Vectorized (Visual): {embedded_products} ({(embedded_products/total_products*100) if total_products else 0:.1f}%)")
    print(f"   - Classified (Taxonomy): {classified_products} ({(classified_products/total_products*100) if total_products else 0:.1f}%)")
    print(f"   - Clustered (Grouped): {clustered_products} ({(clustered_products/total_products*100) if total_products else 0:.1f}%)")

    # 2. Data Quality
    products_no_image = Product.objects.filter(Q(url_image_s3__isnull=True) | Q(url_image_s3='')).count()
    products_unknown_concept = Product.objects.filter(taxonomy_concept='UNKNOWN').count()
    
    print(f"\n2. 🧐 DATA QUALITY:")
    print(f"   - Products without Images: {products_no_image} ({(products_no_image/total_products*100) if total_products else 0:.1f}%)")
    print(f"   - Classified as 'UNKNOWN': {products_unknown_concept} ({(products_unknown_concept/classified_products*100) if classified_products else 0:.1f}%)")

    # 3. Concepts vs Products
    unique_concepts = Product.objects.exclude(taxonomy_concept__isnull=True).exclude(taxonomy_concept='').values('taxonomy_concept').distinct().count()
    
    print(f"\n3. 🧠 CONCEPTS VS PRODUCTS:")
    print(f"   - Unique Concepts Found: {unique_concepts}")
    if classified_products > 0 and unique_concepts > 0:
        print(f"   - Avg Products per Concept: {classified_products / unique_concepts:.1f}")
    
    # 4. Top Concepts
    print(f"\n4. 🏷️ TOP 10 CONCEPTS (By Volume):")
    top_concepts = Product.objects.exclude(taxonomy_concept__isnull=True).values('taxonomy_concept').annotate(count=Count('product_id')).order_by('-count')[:10]
    for c in top_concepts:
        print(f"   - {c['taxonomy_concept']}: {c['count']} products")

    # 5. Market Saturation
    total_clusters = UniqueProductCluster.objects.count()
    avg_competitors = UniqueProductCluster.objects.aggregate(avg=Avg('total_competitors'))['avg']
    
    print(f"\n5. 🏙️ MARKET SATURATION (CLUSTERS):")
    print(f"   - Total Unique Clusters (Distinct Items): {total_clusters}")
    if avg_competitors:
         print(f"   - Avg Competitors per Item: {avg_competitors:.2f}")
    else:
         print("   - Avg Competitors per Item: N/A")
    
    # Most saturated clusters
    print("\n   🔥 TOP 5 MOST SATURATED CLUSTERS:")
    saturated_clusters = UniqueProductCluster.objects.order_by('-total_competitors')[:5]
    for cluster in saturated_clusters:
        name = cluster.concept_name
        if not name and cluster.representative_product:
            name = cluster.representative_product.taxonomy_concept
        
        print(f"   - Cluster {cluster.cluster_id} ({name}): {cluster.total_competitors} competitors")

if __name__ == "__main__":
    analyze()
