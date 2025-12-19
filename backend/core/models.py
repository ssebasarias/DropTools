from django.db import models

class Warehouse(models.Model):
    warehouse_id = models.BigIntegerField(primary_key=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'warehouses'
        # managed = True (Default)

    def __str__(self):
        return f"Warehouse {self.warehouse_id} - {self.city}"


class Supplier(models.Model):
    supplier_id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    store_name = models.CharField(max_length=255, null=True, blank=True)
    plan_name = models.CharField(max_length=100, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    reputation_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'suppliers'

    def __str__(self):
        return f"{self.store_name or self.name}"


# Intento de cargar VectorField de pgvector, fallback a list si no está instalado en local dev
try:
    from pgvector.django import VectorField
except ImportError:
    # Hack for compatibility when pgvector is not installed (e.g. local Windows without lib)
    class VectorField(models.JSONField):
        def __init__(self, *args, **kwargs):
            kwargs.pop('dimensions', None) # Swallow dimensions arg
            super().__init__(*args, **kwargs)


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    # Cerebro Semántico (384 dimensiones)
    embedding = VectorField(dimensions=384, null=True, blank=True)
    
    # Validación Capa 4 (Intención y Coherencia)
    semantic_coherence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    intent_validation_status = models.CharField(max_length=50, default='PENDING')

    # Taxonomía (Capa 5 - Orden)
    taxonomy_type = models.CharField(max_length=50, default='UNKNOWN') # INDUSTRY, CONCEPT, PRODUCT
    suggested_parent = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'categories'

    def __str__(self):
        return self.name

# ... (El resto del archivo se mantiene igual hasta el final, donde agregamos la nueva clase) ...

class MarketplaceFeedback(models.Model):
    id = models.BigAutoField(primary_key=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='feedback')
    marketplace = models.CharField(max_length=50) # 'mercadolibre', 'amazon'
    feedback_type = models.CharField(max_length=20) # 'review', 'question'
    text_content = models.TextField()
    
    # Vector (384 dim)
    embedding = VectorField(dimensions=384, null=True, blank=True)
    
    posted_at = models.DateField(null=True, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_feedback'


class FutureEvent(models.Model):
    """
    Tabla Maestra de Eventos Vectorizados (Reemplaza al MD estático).
    Permite cruzar 'Navidad' con categorías semánticamente similares en DB.
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    date_start = models.DateField()
    date_end = models.DateField(null=True, blank=True)
    prep_days = models.IntegerField(default=30)
    keywords = models.TextField(help_text="Keywords base para generar el vector")
    embedding = VectorField(dimensions=384, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'future_events'

    def __str__(self):
        return f"{self.name} ({self.date_start})"





class Product(models.Model):
    product_id = models.BigIntegerField(primary_key=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, db_column='supplier_id', null=True, blank=True)
    sku = models.CharField(max_length=100, null=True, blank=True)
    title = models.TextField()
    description = models.TextField(null=True, blank=True)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    suggested_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    profit_margin = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    product_type = models.CharField(max_length=50, null=True, blank=True)
    url_image_s3 = models.TextField(null=True, blank=True)
    
    # Taxonomía Jerárquica (V7 - Agent 1 Output)
    taxonomy_concept = models.CharField(max_length=255, null=True, blank=True) # "Silla Gamer"
    taxonomy_industry = models.CharField(max_length=255, null=True, blank=True) # "Muebles"
    taxonomy_level = models.CharField(max_length=50, null=True, blank=True) # "CONCEPT", "PRODUCT"
    
    # Metadata de Rastreo (V2)
    source_platform = models.CharField(max_length=50, default='dropi', null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=['-profit_margin', '-created_at']),
        ]

    def __str__(self):
        return f"{self.title[:50]}"


class ProductCategory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='product_id')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, db_column='category_id')

    class Meta:
        db_table = 'product_categories'
        unique_together = ('product', 'category')


class ProductStockLog(models.Model):
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='product_id')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, db_column='warehouse_id')
    stock_qty = models.IntegerField()
    snapshot_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_stock_log'


class UniqueProductCluster(models.Model):
    cluster_id = models.BigAutoField(primary_key=True)
    representative_product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        db_column='representative_product_id',
        related_name='clusters',
        null=True,
        blank=True
    )
    # Métricas de Oferta (Internas)
    total_competitors = models.IntegerField(default=1)
    average_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    saturation_score = models.CharField(max_length=20, null=True, blank=True)
    
    # Identidad Humana (V2)
    concept_name = models.CharField(max_length=255, null=True, blank=True)

    # Máquina de Estados (V2 - Critical)
    analysis_level = models.IntegerField(default=0) # 0=Nuevo, 1=Trends Checked, 2=Shopify Checked, 3=Full Audit
    is_discarded = models.BooleanField(default=False)
    discard_reason = models.CharField(max_length=255, null=True, blank=True)
    is_candidate = models.BooleanField(default=False) # True = Pasó filtros básicos

    # Inteligencia de Mercado - DEMANDA (V2)
    trend_score = models.IntegerField(default=0) # 0-100 (Google Trends)
    search_volume_estimate = models.IntegerField(null=True, blank=True)
    seasonality_flag = models.CharField(max_length=50, null=True, blank=True)

    # Inteligencia de Mercado - REALIDAD (V2)
    market_avg_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    potential_margin = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    market_saturation_level = models.CharField(max_length=20, null=True, blank=True)

    # Opportunity Score & Taxonomy (V6)
    market_opportunity_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    taxonomy_type = models.CharField(max_length=50, default='UNKNOWN')
    
    # Saturation Filtering (V7 - Embudo)
    dropi_competition_tier = models.CharField(max_length=20, default='LOW', null=True, blank=True) # LOW, MID, HIGH, SATURATED
    
    validation_log = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'unique_product_clusters'

    def __str__(self):
        return f"Cluster {self.cluster_id} - {self.concept_name or 'Unknown'} ({self.total_competitors} sellers)"





class ProductClusterMembership(models.Model):
    product = models.OneToOneField(
        Product, 
        on_delete=models.CASCADE,
        db_column='product_id',
        primary_key=True,
        related_name='cluster_membership'
    )
    cluster = models.ForeignKey(
        UniqueProductCluster,
        on_delete=models.CASCADE,
        db_column='cluster_id',
        related_name='members'
    )
    match_confidence = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    match_method = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = 'product_cluster_membership'

    def __str__(self):
        return f"{self.product.title[:30]} in Cluster {self.cluster.cluster_id}"


class ProductEmbedding(models.Model):
    product = models.OneToOneField(
        Product, 
        on_delete=models.CASCADE, 
        db_column='product_id', 
        primary_key=True
    )
    # Vector Visual (768 dim for CLIP Large)
    embedding_visual = VectorField(dimensions=768, null=True, blank=True)
    
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'product_embeddings'
        # managed = True

class AIFeedback(models.Model):
    id = models.BigAutoField(primary_key=True)
    product_id = models.BigIntegerField()
    candidate_id = models.BigIntegerField()
    decision = models.CharField(max_length=50, null=True, blank=True) # MATCH / REJECT / HYPOTHETICAL
    feedback = models.CharField(max_length=50) # CORRECT / INCORRECT
    
    # Rich Data for ML Training
    visual_score = models.FloatField(default=0.0)
    text_score = models.FloatField(default=0.0)
    final_score = models.FloatField(default=0.0)
    match_method = models.CharField(max_length=50, null=True, blank=True)
    active_weights = models.JSONField(default=dict) # Snapshot of weights used
    
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_feedback'

class ClusterConfig(models.Model):
    id = models.BigAutoField(primary_key=True)
    weight_visual = models.FloatField(default=0.6)
    weight_text = models.FloatField(default=0.4)
    threshold_visual_rescue = models.FloatField(default=0.15)
    threshold_text_rescue = models.FloatField(default=0.95)
    threshold_hybrid = models.FloatField(default=0.68)
    updated_at = models.DateTimeField(auto_now=True)
    version_note = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'cluster_config'

class ClusterDecisionLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    product_id = models.BigIntegerField()
    candidate_id = models.BigIntegerField()
    title_a = models.TextField(null=True, blank=True)
    title_b = models.TextField(null=True, blank=True)
    image_a = models.TextField(null=True, blank=True)
    image_b = models.TextField(null=True, blank=True)
    visual_score = models.FloatField(null=True, blank=True)
    text_score = models.FloatField(null=True, blank=True)
    final_score = models.FloatField(null=True, blank=True)
    decision = models.CharField(max_length=50, null=True, blank=True)  # MATCH / REJECT
    match_method = models.CharField(max_length=50, null=True, blank=True)
    active_weights = models.JSONField(default=dict, null=True, blank=True)

    class Meta:
        db_table = 'cluster_decision_logs'
        ordering = ['-timestamp']


class MarketIntelligenceLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    cluster = models.ForeignKey(UniqueProductCluster, on_delete=models.CASCADE, db_column='cluster_id', related_name='market_logs', null=True, blank=True)
    source = models.CharField(max_length=50) # "google_trends", "shopify_search"
    data_point = models.CharField(max_length=100) # "trend_score", "competitor_price"
    value_text = models.TextField(null=True, blank=True)
    value_numeric = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Contexto Vectorial (¿Qué vector generó este hallazgo?). 
    embedding_context = VectorField(dimensions=384, null=True, blank=True)
    snapshot_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'market_intelligence_logs'

