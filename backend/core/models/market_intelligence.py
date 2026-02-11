from django.db import models
from django.contrib.postgres.fields import ArrayField
from .base import VectorField
from .clustering import UniqueProductCluster


class MarketIntelligenceLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    cluster = models.ForeignKey(UniqueProductCluster, on_delete=models.CASCADE, db_column='cluster_id', related_name='market_logs', null=True, blank=True)
    source = models.CharField(max_length=50)  # "google_trends", "shopify_search"
    data_point = models.CharField(max_length=100)  # "trend_score", "competitor_price"
    value_text = models.TextField(null=True, blank=True)
    value_numeric = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Contexto Vectorial (Que vector genero este hallazgo?). 
    embedding_context = VectorField(dimensions=384, null=True, blank=True)
    snapshot_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'market_intelligence_logs'


class DomainReputation(models.Model):
    """
    Tabla maestra de dominios detectados (Cache Layer).
    Evita re-analizar la misma tienda 100 veces.
    """
    domain = models.CharField(max_length=255, unique=True, db_index=True)
    is_shopify = models.BooleanField(null=True, blank=True)  # None=Not Checked, True=Shopify, False=Other
    
    # Pre-Filter Score & Audit (DSA v1.0)
    shopify_likely_score = models.FloatField(default=0.0)  # 0.0 - 1.0
    shopify_likely_reasons = models.JSONField(default=dict, blank=True)  # {"cdn": true, "cart": false...}
    
    shopify_last_checked_at = models.DateTimeField(null=True, blank=True)
    shopify_cache_expires_at = models.DateTimeField(null=True, blank=True)  # TTL Explicito
    
    # Metadata fija del dominio
    pixel_ids = ArrayField(models.CharField(max_length=50), blank=True, null=True)
    detected_apps = ArrayField(models.CharField(max_length=50), blank=True, null=True)
    
    # Ads Cache (TTL 7 dias conceptual)
    has_active_ads = models.BooleanField(default=False)
    ads_last_checked_at = models.DateTimeField(null=True, blank=True)
    ads_cache_expires_at = models.DateTimeField(null=True, blank=True)  # TTL Explicito
    ads_library_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Ads Evidence (DSA v1.0)
    ads_count_recent = models.IntegerField(default=0)  # Anuncios activos ultimos 30 dias
    ads_evidence = models.JSONField(default=dict, blank=True)  # {"screenshot": "...", "copy": "..."}

    class Meta:
        db_table = 'domain_reputation'


class MarketAnalysisReport(models.Model):
    """
    Cabecera de un análisis de saturación para un cluster.
    """
    cluster = models.ForeignKey(UniqueProductCluster, on_delete=models.CASCADE, related_name='market_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Fingerprint usado
    search_fingerprint = models.JSONField(default=dict)  # Keywords, queries usadas
    
    # Métricas Raw
    candidates_found_raw = models.IntegerField(default=0)  # Total URLs antes de verificar
    shopify_likely_candidates_count = models.IntegerField(default=0)  # Circuit Breaker Counter (DSA v1.0)
    candidates_processed = models.IntegerField(default=0)  # Cuantos pasaron a verificacion
    
    # Resultados Verificados
    direct_competitors_count = models.IntegerField(default=0)  # Match Visual >= Threshold (Direct)
    indirect_competitors_count = models.IntegerField(default=0)  # Match Visual >= Threshold (Indirect)
    
    # Validación de Mercado
    competitors_with_ads = models.IntegerField(default=0)
    
    # Scores Finales
    supplier_saturation_score = models.FloatField(default=0.0)  # Base Dropi
    market_saturation_score = models.FloatField(default=0.0)  # Base Shopify Findings
    final_score = models.FloatField(default=0.0)
    
    # Audit Log (DSA v1.0 - Debugging y Trazabilidad)
    audit_log = models.JSONField(default=list, blank=True)  # Logs del proceso de discovery
    
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
    visual_similarity = models.FloatField(null=True)  # Cosine Similarity (1.0 = Idéntico)
    match_type = models.CharField(max_length=20)  # DIRECT, INDIRECT, REJECTED
    
    class Meta:
        db_table = 'competitor_findings'
        indexes = [
            models.Index(fields=['report', 'match_type']),
        ]
