from django.db import models
from .base import VectorField, EMBED_DIM
from .product import Product


class ConceptWeights(models.Model):
    """
    Tabla de Pesos Dinámicos por Concepto (Personalidad del Clusterizer).
    Usa COSINE SIMILARITY (Mayor es mejor).
    """
    concept = models.CharField(max_length=255, primary_key=True)  # "Tenis Deportivos", "DEFAULT"
    
    weight_visual = models.FloatField(default=0.6)
    weight_text = models.FloatField(default=0.4)
    
    # Clustering Thresholds
    threshold_hybrid = models.FloatField(default=0.68)
    
    # Verification Thresholds (DSA v1.0 - Cosine Similarity)
    similarity_threshold_direct = models.FloatField(default=0.80)  # Very high similarity
    similarity_threshold_indirect = models.FloatField(default=0.65)  # Broad similarity
    
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
    visual_centroid = VectorField(dimensions=EMBED_DIM, null=True, blank=True)  # Promedio del cluster
    
    # 3 Medoids Explicit (VectorFields for Robustness)
    visual_medoid_1 = VectorField(dimensions=EMBED_DIM, null=True, blank=True)
    visual_medoid_2 = VectorField(dimensions=EMBED_DIM, null=True, blank=True)
    visual_medoid_3 = VectorField(dimensions=EMBED_DIM, null=True, blank=True)
    
    medoid_meta = models.JSONField(default=dict, blank=True)  # {"ids": [101, 202, 303], "origins": [...]}

    # Maquina de Estados (V2 - Critical)
    analysis_level = models.IntegerField(default=0)  # 0=Nuevo, 1=Trends Checked, 2=Shopify Checked, 3=Full Audit
    is_discarded = models.BooleanField(default=False)
    discard_reason = models.CharField(max_length=255, null=True, blank=True)
    is_candidate = models.BooleanField(default=False)  # True = Paso filtros basicos

    # Inteligencia de Mercado - DEMANDA (V2)
    trend_score = models.IntegerField(default=0)  # 0-100 (Google Trends)
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
    dropi_competition_tier = models.CharField(max_length=20, default='LOW', null=True, blank=True)  # LOW, MID, HIGH, SATURATED
    
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


class AIFeedback(models.Model):
    id = models.BigAutoField(primary_key=True)
    product_id = models.BigIntegerField()
    candidate_id = models.BigIntegerField()
    decision = models.CharField(max_length=50, null=True, blank=True)  # MATCH / REJECT / HYPOTHETICAL
    feedback = models.CharField(max_length=50)  # CORRECT / INCORRECT
    
    # Rich Data for ML Training
    visual_score = models.FloatField(default=0.0)
    text_score = models.FloatField(default=0.0)
    final_score = models.FloatField(default=0.0)
    match_method = models.CharField(max_length=50, null=True, blank=True)
    active_weights = models.JSONField(default=dict)  # Snapshot of weights used
    
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
