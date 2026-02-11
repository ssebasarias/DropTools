from django.db import models
from .base import VectorField, EMBED_DIM
from .warehouse import Supplier, Warehouse
from .category import Category


class Product(models.Model):
    # Clave compuesta: (product_id, supplier_id)
    # Permite que múltiples proveedores vendan el mismo producto
    product_id = models.BigIntegerField(primary_key=True)  # RESTORED PK to avoid migration hell

    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.CASCADE, 
        db_column='supplier_id',
        null=True,  # Restore to avoid interactive prompt
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
    taxonomy_concept = models.CharField(max_length=255, null=True, blank=True)  # "Silla Gamer"
    taxonomy_industry = models.CharField(max_length=255, null=True, blank=True)  # "Muebles"
    taxonomy_level = models.CharField(max_length=50, null=True, blank=True)  # "CONCEPT", "PRODUCT"
    
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
