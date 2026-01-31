
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# -----------------------------------------------------------------------------
# CONSTANTS CONTRACT (DSA v1.0)
# -----------------------------------------------------------------------------
EMBED_DIM = 1152 # SigLIP SO400M patch14-384
EMBED_NORMALIZE = True

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


# Intento de cargar VectorField de pgvector, fallback a list si no existe
try:
    from pgvector.django import VectorField
except ImportError:
    # Hack for compatibility when pgvector is not installed
    class VectorField(models.JSONField):
        def __init__(self, *args, **kwargs):
            kwargs.pop('dimensions', None) # Swallow dimensions arg
            super().__init__(*args, **kwargs)
# Require pgvector for correct VectorField support. Fail fast if missing
try:
    from pgvector.django import VectorField
except Exception as e:
    raise RuntimeError(
        "pgvector.django.VectorField is required. Install 'pgvector' and enable the 'vector' extension in Postgres. "
        f"Original error: {e}"
    )


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    # Cerebro Semantico (384 dimensiones)
    embedding = VectorField(dimensions=384, null=True, blank=True)
    
    # Validacion Capa 4 (Intencion y Coherencia)
    semantic_coherence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    intent_validation_status = models.CharField(max_length=50, default='PENDING')

    # Taxonomia (Capa 5 - Orden)
    taxonomy_type = models.CharField(max_length=50, default='UNKNOWN') # INDUSTRY, CONCEPT, PRODUCT
    suggested_parent = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'categories'

    def __str__(self):
        return self.name

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
    Tabla Maestra de Eventos Vectorizados (Reemplaza al MD estatico).
    Permite cruzar 'Navidad' con categorias semanticamente similares en DB.
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
    # Clave compuesta: (product_id, supplier_id)
    # Permite que mÃºltiples proveedores vendan el mismo producto
    product_id = models.BigIntegerField(primary_key=True)  # RESTORED PK to avoid migration hell

    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.CASCADE, 
        db_column='supplier_id',
        null=True, # Restore to avoid interactive prompt
        blank=True
    )

    sku = models.CharField(max_length=100, null=True, blank=True)

    title = models.TextField()
    description = models.TextField(null=True, blank=True)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    suggested_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    profit_margin = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    product_type = models.CharField(max_length=50, null=True, blank=True)
    url_image_s3 = models.TextField(null=True, blank=True)
    
    # Taxonomia Jerarquica (V7 - Agent 1 Output)
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
        # Clave compuesta: Un proveedor puede vender un producto solo UNA vez
        # Diferentes proveedores pueden vender el MISMO producto (competencia)
        unique_together = ('product_id', 'supplier')
        indexes = [
            models.Index(fields=['-profit_margin', '-created_at']),
            models.Index(fields=['product_id']),  # Para bÃºsquedas por producto
            models.Index(fields=['supplier']),     # Para bÃºsquedas por proveedor
        ]

    def __str__(self):
        supplier_name = self.supplier.store_name if self.supplier else 'N/A'
        return f"{self.title[:50]} (Proveedor: {supplier_name})"




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








class ConceptWeights(models.Model):
    """
    Tabla de Pesos DinÃ¡micos por Concepto (Personalidad del Clusterizer).
    Usa COSINE SIMILARITY (Mayor es mejor).
    """
    concept = models.CharField(max_length=255, primary_key=True) # "Tenis Deportivos", "DEFAULT"
    
    weight_visual = models.FloatField(default=0.6)
    weight_text = models.FloatField(default=0.4)
    
    # Clustering Thresholds
    threshold_hybrid = models.FloatField(default=0.68)
    
    # Verification Thresholds (DSA v1.0 - Cosine Similarity)
    similarity_threshold_direct = models.FloatField(default=0.80) # Very high similarity
    similarity_threshold_indirect = models.FloatField(default=0.65) # Broad similarity
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'concept_weights'

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
    # Metricas de Oferta (Internas)
    total_competitors = models.IntegerField(default=1)
    average_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    saturation_score = models.CharField(max_length=20, null=True, blank=True)
    
    # Identidad Humana (V2)
    concept_name = models.CharField(max_length=255, null=True, blank=True)


    # Identidad Visual Avanzada (DSA v1.0)
    visual_centroid = VectorField(dimensions=EMBED_DIM, null=True, blank=True) # Promedio del cluster
    
    # 3 Medoids Explicit (VectorFields for Robustness)
    visual_medoid_1 = VectorField(dimensions=EMBED_DIM, null=True, blank=True)
    visual_medoid_2 = VectorField(dimensions=EMBED_DIM, null=True, blank=True)
    visual_medoid_3 = VectorField(dimensions=EMBED_DIM, null=True, blank=True)
    
    medoid_meta = models.JSONField(default=dict, blank=True) # {"ids": [101, 202, 303], "origins": [...]}


    # Maquina de Estados (V2 - Critical)
    analysis_level = models.IntegerField(default=0) # 0=Nuevo, 1=Trends Checked, 2=Shopify Checked, 3=Full Audit
    is_discarded = models.BooleanField(default=False)
    discard_reason = models.CharField(max_length=255, null=True, blank=True)
    is_candidate = models.BooleanField(default=False) # True = Paso filtros basicos

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


    # Vector Visual (Use Config Contract)
    embedding_visual = VectorField(dimensions=EMBED_DIM, null=True, blank=True)

    
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
    # Contexto Vectorial (Que vector genero este hallazgo?). 
    embedding_context = VectorField(dimensions=384, null=True, blank=True)
    snapshot_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'market_intelligence_logs'



# -----------------------------------------------------------------------------
# MARKET SATURATION ANALYZER MODELS (ADDED V8)
# -----------------------------------------------------------------------------


class DomainReputation(models.Model):
    """
    Tabla maestra de dominios detectados (Cache Layer).
    Evita re-analizar la misma tienda 100 veces.
    """
    domain = models.CharField(max_length=255, unique=True, db_index=True)
    is_shopify = models.BooleanField(null=True, blank=True) # None=Not Checked, True=Shopify, False=Other
    
    # Pre-Filter Score & Audit (DSA v1.0)
    shopify_likely_score = models.FloatField(default=0.0) # 0.0 - 1.0
    shopify_likely_reasons = models.JSONField(default=dict, blank=True) # {"cdn": true, "cart": false...}
    
    shopify_last_checked_at = models.DateTimeField(null=True, blank=True)
    shopify_cache_expires_at = models.DateTimeField(null=True, blank=True) # TTL Explicito
    
    # Metadata fija del dominio
    pixel_ids = ArrayField(models.CharField(max_length=50), blank=True, null=True)
    detected_apps = ArrayField(models.CharField(max_length=50), blank=True, null=True)
    
    # Ads Cache (TTL 7 dias conceptual)
    has_active_ads = models.BooleanField(default=False)
    ads_last_checked_at = models.DateTimeField(null=True, blank=True)
    ads_cache_expires_at = models.DateTimeField(null=True, blank=True) # TTL Explicito
    ads_library_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Ads Evidence (DSA v1.0)
    ads_count_recent = models.IntegerField(default=0) # Anuncios activos ultimos 30 dias
    ads_evidence = models.JSONField(default=dict, blank=True) # {"screenshot": "...", "copy": "..."}

    class Meta:
        db_table = 'domain_reputation'

class MarketAnalysisReport(models.Model):
    """
    Cabecera de un anÃ¡lisis de saturaciÃ³n para un cluster.
    """
    cluster = models.ForeignKey(UniqueProductCluster, on_delete=models.CASCADE, related_name='market_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Fingerprint usado
    search_fingerprint = models.JSONField(default=dict) # Keywords, queries usadas
    
    # MÃ©tricas Raw
    candidates_found_raw = models.IntegerField(default=0) # Total URLs antes de verificar
    shopify_likely_candidates_count = models.IntegerField(default=0) # Circuit Breaker Counter (DSA v1.0)
    candidates_processed = models.IntegerField(default=0) # Cuantos pasaron a verificacion
    

    # Resultados Verificados
    direct_competitors_count = models.IntegerField(default=0) # Match Visual >= Threshold (Direct)
    indirect_competitors_count = models.IntegerField(default=0) # Match Visual >= Threshold (Indirect)

    
    # ValidaciÃ³n de Mercado
    competitors_with_ads = models.IntegerField(default=0)
    
    # Scores Finales
    supplier_saturation_score = models.FloatField(default=0.0) # Base Dropi
    market_saturation_score = models.FloatField(default=0.0) # Base Shopify Findings
    final_score = models.FloatField(default=0.0)
    
    # Audit Log (DSA v1.0 - Debugging y Trazabilidad)
    audit_log = models.JSONField(default=list, blank=True) # Logs del proceso de discovery
    
    # Estado (Enum: 'LOW_OPP', 'TESTABLE', 'HIGH_SAT', 'WINNER')
    market_state = models.CharField(max_length=50, default='PENDING')

    class Meta:
        db_table = 'market_analysis_reports'


class CompetitorFinding(models.Model):
    """
    Detalle: Un competidor encontrado para un anÃ¡lisis especÃ­fico.
    """
    report = models.ForeignKey(MarketAnalysisReport, on_delete=models.CASCADE, related_name='findings')
    domain_ref = models.ForeignKey(DomainReputation, on_delete=models.SET_NULL, null=True)
    
    url_found = models.URLField(max_length=1000)
    title_detected = models.CharField(max_length=500, blank=True)
    price_detected = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    

    # Evidencia Visual
    image_url = models.URLField(max_length=1000, blank=True)
    visual_similarity = models.FloatField(null=True) # Cosine Similarity (1.0 = IdÃ©ntico)
    match_type = models.CharField(max_length=20) # DIRECT, INDIRECT, REJECTED

    
    class Meta:
        db_table = 'competitor_findings'
        indexes = [
            models.Index(fields=['report', 'match_type']),
        ]


# User is now defined in this file (core.models.User)
from django.utils import timezone


# -----------------------------------------------------------------------------
# USER MANAGEMENT (SECURITY / SUBSCRIPTIONS)
# -----------------------------------------------------------------------------

class User(AbstractUser):
    """
    Modelo de usuario unificado que combina:
    - auth_user (login del aplicativo) - heredado de AbstractUser
    - user_profiles (perfil, rol, suscripciÃ³n)
    - dropi_accounts (credenciales Dropi)
    
    Esta es la Ãºnica tabla de usuarios en el sistema.
    """
    
    ROLE_ADMIN = "ADMIN"
    ROLE_CLIENT = "CLIENT"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_CLIENT, "Client"),
    ]
    
    TIER_BRONZE = "BRONZE"
    TIER_SILVER = "SILVER"
    TIER_GOLD = "GOLD"
    TIER_PLATINUM = "PLATINUM"
    TIER_CHOICES = [
        (TIER_BRONZE, "Bronze"),
        (TIER_SILVER, "Silver"),
        (TIER_GOLD, "Gold"),
        (TIER_PLATINUM, "Platinum"),
    ]
    
    # Campos de user_profiles (perfil y suscripciÃ³n)
    full_name = models.CharField(max_length=120, blank=True, default="")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    subscription_tier = models.CharField(max_length=10, choices=TIER_CHOICES, default=TIER_BRONZE)
    subscription_active = models.BooleanField(default=False)
    execution_time = models.TimeField(null=True, blank=True, help_text="Hora diaria para ejecutar el workflow de reportes (formato HH:MM)")
    
    # Campos de dropi_accounts (credenciales Dropi - cuenta principal)
    dropi_email = models.EmailField(max_length=255, null=True, blank=True, help_text="Email de la cuenta Dropi principal")
    dropi_password = models.CharField(max_length=255, null=True, blank=True, help_text="Password de la cuenta Dropi (string simple, no encriptado)")

    # Estimación de carga (usado en reservas por hora)
    monthly_orders_estimate = models.PositiveIntegerField(null=True, blank=True, help_text="Órdenes mensuales aproximadas")

    # Timestamps adicionales
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["email"]),
            models.Index(fields=["role", "subscription_tier"]),
            models.Index(fields=["subscription_active"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.username} ({self.role}/{self.subscription_tier})"
    
    def is_admin(self) -> bool:
        """Retorna True si el usuario es admin"""
        return self.role == self.ROLE_ADMIN or self.is_superuser
    
    def get_dropi_password_plain(self) -> str:
        """
        Retorna la contraseÃ±a Dropi sin encriptar (siempre como string simple)
        """
        return self.dropi_password or ""
    
    def set_dropi_password_plain(self, raw: str) -> None:
        """
        Guarda la contraseÃ±a Dropi como string simple (sin encriptar)
        """
        self.dropi_password = raw or ""


# DropiAccount & UserProfile removed as per user request to consolidate all user data in 'User' model.


class OrderReport(models.Model):
    """
    Tabla de reportes de Ã³rdenes generados por el bot reporter.
    Reemplaza el sistema de checkpoints CSV por una base de datos mÃ¡s eficiente.
    """
    
    STATUS_CHOICES = [
        ('proximo_a_reportar', 'PrÃ³ximo a Reportar'),
        ('reportado', 'Reportado'),
        ('error', 'Error'),
        ('no_encontrado', 'No Encontrado'),
        ('already_has_case', 'Ya Tiene Caso'),
        ('cannot_generate_yet', 'No Se Puede Generar AÃºn'),
        ('in_movement', 'En Movimiento'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='order_reports')
    order_phone = models.CharField(max_length=50, db_index=True, help_text="NÃºmero de telÃ©fono de la orden")
    order_id = models.CharField(max_length=100, null=True, blank=True, help_text="ID de la orden en Dropi")
    tracking_number = models.CharField(max_length=100, null=True, blank=True, help_text="NÃºmero de guÃ­a / Tracking")
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='proximo_a_reportar')
    report_generated = models.BooleanField(default=False, help_text="True si el reporte se generÃ³ exitosamente")
    
    # InformaciÃ³n adicional de la orden
    customer_name = models.CharField(max_length=255, null=True, blank=True, help_text="Nombre del cliente")
    product_name = models.TextField(null=True, blank=True, help_text="Nombre del producto vinculado a la orden")
    order_state = models.CharField(max_length=100, null=True, blank=True, help_text="Estado actual de la orden en Dropi")
    days_since_order = models.IntegerField(null=True, blank=True, help_text="DÃ­as transcurridos desde la orden (del CSV)")
    
    # Control de tiempos
    next_attempt_time = models.DateTimeField(null=True, blank=True, help_text="PrÃ³ximo intento (para estados que requieren espera)")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'order_reports'
        indexes = [
            models.Index(fields=['user', 'order_phone']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'report_generated']),
            models.Index(fields=['order_phone']),  # Para bÃºsquedas rÃ¡pidas
            models.Index(fields=['next_attempt_time']),  # Para filtrar por tiempo
        ]
        # Un usuario no puede tener mÃºltiples reportes activos para la misma orden
        # (pero puede tener mÃºltiples intentos histÃ³ricos si falla)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'order_phone'],
                condition=models.Q(status__in=['reportado', 'proximo_a_reportar']),
                name='unique_active_report_per_order'
            )
        ]
    
    def __str__(self):
        return f"OrderReport {self.id} - {self.order_phone} ({self.status})"


class WorkflowProgress(models.Model):
    """
    Rastrea el progreso del workflow de reportes para cada usuario
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('step1_running', 'Paso 1: Descargando Reportes'),
        ('step1_completed', 'Paso 1: Completado'),
        ('step2_running', 'Paso 2: Comparando Reportes'),
        ('step2_completed', 'Paso 2: Completado'),
        ('step3_running', 'Paso 3: Reportando CAS'),
        ('step3_completed', 'Paso 3: Completado'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workflow_progresses')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    
    # Mensajes de progreso
    current_message = models.TextField(null=True, blank=True, help_text="Mensaje actual del progreso")
    messages = models.JSONField(default=list, help_text="Lista de mensajes de progreso")
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    step1_completed_at = models.DateTimeField(null=True, blank=True)
    step2_completed_at = models.DateTimeField(null=True, blank=True)
    step3_completed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflow_progress'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'started_at']),
        ]
        ordering = ['-started_at']
    
    def __str__(self):
        return f"WorkflowProgress {self.id} - {self.user.email} ({self.status})"


# -----------------------------------------------------------------------------
# REPORT BATCH MANAGEMENT (ADDED FOR DB-BASED REPORTING)
# -----------------------------------------------------------------------------

class ReportBatch(models.Model):
    """
    Representa un lote de descarga de reportes de Dropi.
    Reemplaza la dependencia de carpetas/archivos fÃ­sicos y permite trazabilidad total.
    """
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='report_batches')
    account_email = models.EmailField(max_length=255, help_text="Email de la cuenta Dropi de donde vino este reporte")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default="SUCCESS") # SUCCESS, FAILED, PROCESSING
    
    # Metadata opcional del lote
    total_records = models.IntegerField(default=0, help_text="Total de filas leÃ­das del Excel")

    class Meta:
        db_table = 'report_batches'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['account_email']),
        ]
        verbose_name = "Lote de Reporte"
        verbose_name_plural = "Lotes de Reportes"

    def __str__(self):
        return f"Batch {self.id} - {self.account_email} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class RawOrderSnapshot(models.Model):
    """
    Una 'foto' de una orden en un momento especÃ­fico (traÃ­da de un ReportBatch).
    Contiene la data cruda del Excel de Dropi mapeada a columnas estructuradas.
    Permite comparar estados entre Batches para detectar 'Sin Movimiento'.
    """
    id = models.BigAutoField(primary_key=True)
    batch = models.ForeignKey(ReportBatch, on_delete=models.CASCADE, related_name='snapshots')
    
    # IDs e Identificadores Clave
    dropi_order_id = models.CharField(max_length=100, db_index=True, help_text="Columna: ID")
    shopify_order_id = models.CharField(max_length=100, null=True, blank=True, help_text="Columna: NUMERO DE PEDIDO DE TIENDA")
    guide_number = models.CharField(max_length=100, null=True, blank=True, help_text="Columna: NÃšMERO GUIA")
    
    # Estado y LogÃ­stica
    current_status = models.CharField(max_length=100, db_index=True, help_text="Columna: ESTATUS")
    carrier = models.CharField(max_length=100, null=True, blank=True, help_text="Columna: TRANSPORTADORA")
    
    # Cliente
    customer_name = models.CharField(max_length=255, null=True, blank=True, help_text="Columna: NOMBRE CLIENTE")
    customer_phone = models.CharField(max_length=50, db_index=True, null=True, blank=True, help_text="Columna: TELÃ‰FONO")
    customer_email = models.CharField(max_length=255, null=True, blank=True, help_text="Columna: EMAIL")
    address = models.TextField(null=True, blank=True, help_text="Columna: DIRECCION")
    city = models.CharField(max_length=100, null=True, blank=True, help_text="Columna: CIUDAD DESTINO")
    department = models.CharField(max_length=100, null=True, blank=True, help_text="Columna: DEPARTAMENTO DESTINO")

    # Producto
    product_name = models.TextField(null=True, blank=True, help_text="Columna: PRODUCTO")
    product_id = models.CharField(max_length=100, null=True, blank=True, help_text="Columna: PRODUCTO ID")
    sku = models.CharField(max_length=100, null=True, blank=True, db_index=True, help_text="Columna: SKU")
    variation = models.CharField(max_length=255, null=True, blank=True, help_text="Columna: VARIACION")
    quantity = models.IntegerField(default=1, help_text="Columna: CANTIDAD")

    # Finanzas
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Columna: TOTAL DE LA ORDEN")
    profit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Calculado: TOTAL DE LA ORDEN - PRECIO FLETE - PRECIO PROVEEDOR")
    shipping_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Columna: PRECIO FLETE")
    supplier_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Columna: PRECIO PROVEEDOR")

    # Canal / tienda (útiles para análisis por tienda y canal)
    store_type = models.CharField(max_length=50, null=True, blank=True, help_text="Columna: TIPO DE TIENDA")
    store_name = models.CharField(max_length=100, null=True, blank=True, help_text="Columna: TIENDA")

    # Tiempos
    order_date = models.DateField(null=True, blank=True, help_text="Columna: FECHA (convertida a Date)")
    order_time = models.CharField(max_length=20, null=True, blank=True, help_text="Columna: HORA")
    report_date = models.DateField(null=True, blank=True, help_text="Columna: FECHA DE REPORTE")

    class Meta:
        db_table = 'raw_order_snapshots'
        indexes = [
            models.Index(fields=['dropi_order_id']),
            models.Index(fields=['current_status']),
            models.Index(fields=['batch', 'current_status']), # Optimiza queries de comparaciÃ³n
        ]

    def __str__(self):
        return f"Snapshot {self.dropi_order_id} ({self.current_status})"


class OrderMovementReport(models.Model):
    """
    Registro de órdenes detectadas sin movimiento al comparar reportes.
    Sirve como 'cola de trabajo' para los agentes de resolución.
    """
    id = models.BigAutoField(primary_key=True)
    
    # Vinculación
    batch = models.ForeignKey(ReportBatch, on_delete=models.CASCADE, related_name='stagnant_orders', help_text="El reporte donde se detectó (HOY)")
    snapshot = models.ForeignKey(RawOrderSnapshot, on_delete=models.CASCADE, related_name='stagnant_findings', help_text="La foto de la orden hoy")
    
    # Datos calculados en el momento
    days_since_order = models.IntegerField(default=0, help_text="Días desde que se creó la orden hasta hoy")
    
    # Gestión de la incidencia
    is_resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_movement_reports'
        verbose_name = "Orden Sin Movimiento"
        verbose_name_plural = "Órdenes Sin Movimiento"
        indexes = [
            models.Index(fields=['batch', 'is_resolved']),
        ]

    def __str__(self):
        return f"Stagnant Order {self.snapshot.dropi_order_id} ({self.days_since_order} days)"


# -----------------------------------------------------------------------------
# REPORTER SLOT SYSTEM (reservas por hora, rangos, scheduler)
# -----------------------------------------------------------------------------

class ReporterSlotConfig(models.Model):
    """
    Configuración global del sistema de reportes por slot.
    Una sola fila activa (singleton por id=1 o get_or_create).
    """
    max_active_selenium = models.PositiveIntegerField(default=6, help_text="Máximo de procesos Selenium simultáneos")
    estimated_pending_factor = models.DecimalField(
        max_digits=5, decimal_places=4, default=0.08,
        help_text="Factor para estimar órdenes pendientes: monthly_orders * factor"
    )
    range_size = models.PositiveIntegerField(default=100, help_text="Tamaño de cada rango de órdenes a reportar")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reporter_slot_config'
        verbose_name = "Configuración Reporter Slots"
        verbose_name_plural = "Configuraciones Reporter Slots"

    def __str__(self):
        return f"ReporterSlotConfig(max_selenium={self.max_active_selenium}, range_size={self.range_size})"


class ReporterHourSlot(models.Model):
    """
    Una hora del día asignable para ejecución diaria del reporter.
    hour: 0-23 (único).
    """
    hour = models.PositiveSmallIntegerField(unique=True, help_text="Hora del día (0-23)")
    max_users = models.PositiveIntegerField(default=10, help_text="Máximo de usuarios que pueden reservar esta hora")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reporter_hour_slots'
        verbose_name = "Slot horario Reporter"
        verbose_name_plural = "Slots horarios Reporter"
        ordering = ['hour']

    def __str__(self):
        return f"{self.hour:02d}:00 (máx {self.max_users} usuarios)"


class ReporterReservation(models.Model):
    """
    Reserva de un usuario en una hora diaria.
    Un usuario solo puede tener una reserva (una hora).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reporter_reservation'
    )
    slot = models.ForeignKey(
        ReporterHourSlot,
        on_delete=models.CASCADE,
        related_name='reservations'
    )
    monthly_orders_estimate = models.PositiveIntegerField(
        default=0,
        help_text="Órdenes mensuales aproximadas del usuario"
    )
    estimated_pending_orders = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="monthly_orders_estimate * factor (calculado al guardar)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reporter_reservations'
        verbose_name = "Reserva Reporter"
        verbose_name_plural = "Reservas Reporter"
        indexes = [
            models.Index(fields=['slot']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.slot.hour:02d}:00"

    def save(self, *args, **kwargs):
        config = ReporterSlotConfig.objects.first()
        factor = float(config.estimated_pending_factor) if config else 0.08
        self.estimated_pending_orders = self.monthly_orders_estimate * factor
        super().save(*args, **kwargs)


class ReporterRun(models.Model):
    """
    Una ejecución diaria de un slot (una "carrera" del ecosistema de esa hora).
    """
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pendiente'),
        (STATUS_RUNNING, 'En ejecución'),
        (STATUS_COMPLETED, 'Completado'),
        (STATUS_FAILED, 'Fallido'),
    ]

    slot = models.ForeignKey(
        ReporterHourSlot,
        on_delete=models.CASCADE,
        related_name='runs'
    )
    scheduled_at = models.DateTimeField(help_text="Fecha/hora programada (ej. 2025-01-31 10:00:00)")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reporter_runs'
        verbose_name = "Run Reporter"
        verbose_name_plural = "Runs Reporter"
        indexes = [
            models.Index(fields=['slot', 'scheduled_at']),
            models.Index(fields=['status']),
        ]
        ordering = ['-scheduled_at']

    def __str__(self):
        return f"Run {self.slot.hour:02d}:00 @ {self.scheduled_at} ({self.status})"


class ReporterRange(models.Model):
    """
    Un rango de órdenes a reportar para un usuario en una Run.
    range_start/range_end: índices 1-based sobre la lista de OrderMovementReport pendientes.
    """
    STATUS_PENDING = 'pending'
    STATUS_LOCKED = 'locked'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pendiente'),
        (STATUS_LOCKED, 'Bloqueado'),
        (STATUS_PROCESSING, 'Procesando'),
        (STATUS_COMPLETED, 'Completado'),
        (STATUS_FAILED, 'Fallido'),
    ]

    run = models.ForeignKey(
        ReporterRun,
        on_delete=models.CASCADE,
        related_name='ranges'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reporter_ranges'
    )
    range_start = models.PositiveIntegerField(help_text="Índice inicio (1-based)")
    range_end = models.PositiveIntegerField(help_text="Índice fin (inclusive)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.CharField(max_length=255, null=True, blank=True, help_text="task_id del worker")
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reporter_ranges'
        verbose_name = "Rango Reporter"
        verbose_name_plural = "Rangos Reporter"
        indexes = [
            models.Index(fields=['run', 'user', 'range_start']),
            models.Index(fields=['run', 'status']),
        ]

    def __str__(self):
        return f"Range {self.range_start}-{self.range_end} user={self.user_id} ({self.status})"


class ReporterRunUser(models.Model):
    """
    Estado por usuario dentro de una Run (Download+Compare y progreso por rangos).
    """
    DC_PENDING = 'pending'
    DC_RUNNING = 'running'
    DC_COMPLETED = 'completed'
    DC_FAILED = 'failed'
    DC_STATUS_CHOICES = [
        (DC_PENDING, 'Pendiente'),
        (DC_RUNNING, 'Ejecutando'),
        (DC_COMPLETED, 'Completado'),
        (DC_FAILED, 'Fallido'),
    ]

    run = models.ForeignKey(
        ReporterRun,
        on_delete=models.CASCADE,
        related_name='run_users'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reporter_run_users'
    )
    download_compare_status = models.CharField(
        max_length=20,
        choices=DC_STATUS_CHOICES,
        default=DC_PENDING,
        db_index=True
    )
    download_compare_completed_at = models.DateTimeField(null=True, blank=True)
    total_pending_orders = models.PositiveIntegerField(default=0)
    total_ranges = models.PositiveIntegerField(default=0)
    ranges_completed = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reporter_run_users'
        verbose_name = "Run Usuario Reporter"
        verbose_name_plural = "Run Usuarios Reporter"
        unique_together = [('run', 'user')]
        indexes = [
            models.Index(fields=['run', 'user']),
        ]

    def __str__(self):
        return f"RunUser run={self.run_id} user={self.user_id} dc={self.download_compare_status}"

