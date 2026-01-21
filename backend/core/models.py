
from django.db import models
from django.contrib.postgres.fields import ArrayField

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
    # Permite que múltiples proveedores vendan el mismo producto
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
            models.Index(fields=['product_id']),  # Para búsquedas por producto
            models.Index(fields=['supplier']),     # Para búsquedas por proveedor
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
    Tabla de Pesos Dinámicos por Concepto (Personalidad del Clusterizer).
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
    Cabecera de un análisis de saturación para un cluster.
    """
    cluster = models.ForeignKey(UniqueProductCluster, on_delete=models.CASCADE, related_name='market_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Fingerprint usado
    search_fingerprint = models.JSONField(default=dict) # Keywords, queries usadas
    
    # Métricas Raw
    candidates_found_raw = models.IntegerField(default=0) # Total URLs antes de verificar
    shopify_likely_candidates_count = models.IntegerField(default=0) # Circuit Breaker Counter (DSA v1.0)
    candidates_processed = models.IntegerField(default=0) # Cuantos pasaron a verificacion
    

    # Resultados Verificados
    direct_competitors_count = models.IntegerField(default=0) # Match Visual >= Threshold (Direct)
    indirect_competitors_count = models.IntegerField(default=0) # Match Visual >= Threshold (Indirect)

    
    # Validación de Mercado
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
    Detalle: Un competidor encontrado para un análisis específico.
    """
    report = models.ForeignKey(MarketAnalysisReport, on_delete=models.CASCADE, related_name='findings')
    domain_ref = models.ForeignKey(DomainReputation, on_delete=models.SET_NULL, null=True)
    
    url_found = models.URLField(max_length=1000)
    title_detected = models.CharField(max_length=500, blank=True)
    price_detected = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    

    # Evidencia Visual
    image_url = models.URLField(max_length=1000, blank=True)
    visual_similarity = models.FloatField(null=True) # Cosine Similarity (1.0 = Idéntico)
    match_type = models.CharField(max_length=20) # DIRECT, INDIRECT, REJECTED

    
    class Meta:
        db_table = 'competitor_findings'
        indexes = [
            models.Index(fields=['report', 'match_type']),
        ]


from django.contrib.auth.models import User
from django.utils import timezone


# -----------------------------------------------------------------------------
# USER MANAGEMENT (SECURITY / SUBSCRIPTIONS)
# -----------------------------------------------------------------------------

class UserProfile(models.Model):
    """
    Perfil del usuario para:
    - Datos de perfil (nombre)
    - Rol (ADMIN / CLIENT)
    - Suscripción (qué módulos puede usar)

    Nota: El login del aplicativo se maneja con `auth_user` (Django User: email/username + password hasheada).
    Las credenciales externas (Dropi) se modelan aparte para permitir múltiples cuentas por usuario.
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

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile", unique=True)
    full_name = models.CharField(max_length=120, blank=True, default="")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    # Subscription tier controls which client modules are enabled.
    subscription_tier = models.CharField(max_length=10, choices=TIER_CHOICES, default=TIER_BRONZE)
    # If false: user can log in and see UI, but backend should block paid actions (no payments yet).
    subscription_active = models.BooleanField(default=False)

    # NOTE: usamos default=timezone.now para evitar prompt interactivo en migraciones
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Campos legacy (compatibilidad con la tabla existente y UI actual).
    # Se migrarán a `DropiAccount` y luego se podrán eliminar.
    dropi_email = models.EmailField(max_length=255, null=True, blank=True)
    dropi_password = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "user_profiles"

    def __str__(self) -> str:
        return f"{self.user.username} ({self.role}/{self.subscription_tier})"


class DropiAccount(models.Model):
    """
    Cuenta(s) de Dropi asociadas a un usuario.
    Un usuario puede tener múltiples cuentas secundarias (por ejemplo: una para scraper, otra para reporter).
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dropi_accounts")
    label = models.CharField(max_length=50, default="default")
    email = models.EmailField(max_length=255)
    # Stored encrypted-at-rest when encryption key is configured.
    password = models.CharField(max_length=255)
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dropi_accounts"
        indexes = [
            models.Index(fields=["user", "is_default"]),
            models.Index(fields=["email"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "label"], name="uniq_dropi_account_label_per_user"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.label} ({self.email})"

    def get_password_plain(self) -> str:
        """
        Returns decrypted password if encryption is enabled; otherwise returns stored value.
        """
        from .crypto import decrypt_if_needed

        return decrypt_if_needed(self.password or "")

    def set_password_plain(self, raw: str) -> None:
        from .crypto import encrypt_if_needed

        self.password = encrypt_if_needed(raw or "")

    def save(self, *args, **kwargs):
        """
        Encrypt password-at-rest if key is configured and value isn't encrypted yet.
        """
        try:
            from .crypto import encrypt_if_needed

            self.password = encrypt_if_needed(self.password or "")
        except Exception:
            # Fail-open for local dev if crypto isn't configured; do not crash saves.
            pass
        return super().save(*args, **kwargs)
