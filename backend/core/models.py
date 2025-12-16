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


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'categories'

    def __str__(self):
        return self.name


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
    total_competitors = models.IntegerField(default=1)
    average_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    saturation_score = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'unique_product_clusters'

    def __str__(self):
        return f"Cluster {self.cluster_id} - {self.total_competitors} competitors"


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
    # Omitimos campo vectorial pgvector (managed manual o via Field custom, lo dejaremos manual por ahora en migrations)
    # Django no soporta pgvector nativo sin libreria extra, asi que cuidado aqui.
    # Dejamos managed=False SOLO en esta tabla si queremos evitar problemas con el campo vector, 
    # O mejor, lo manejamos pero sabemos que makemigrations ignorará el campo que no está definido aquí.
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
