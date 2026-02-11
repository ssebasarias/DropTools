from django.db import models
from .base import VectorField


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
    taxonomy_type = models.CharField(max_length=50, default='UNKNOWN')  # INDUSTRY, CONCEPT, PRODUCT
    suggested_parent = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'categories'

    def __str__(self):
        return self.name


class MarketplaceFeedback(models.Model):
    id = models.BigAutoField(primary_key=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='feedback')
    marketplace = models.CharField(max_length=50)  # 'mercadolibre', 'amazon'
    feedback_type = models.CharField(max_length=20)  # 'review', 'question'
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
