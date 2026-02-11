from django.db import models
from .base import VectorField


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
