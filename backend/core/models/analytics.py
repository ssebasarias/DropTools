from django.db import models
from django.conf import settings
from .user import User


class AnalyticsDailySnapshot(models.Model):
    """
    Métricas agregadas diarias por usuario.
    Almacena snapshot diario de todas las métricas principales para análisis histórico.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='analytics_daily_snapshots'
    )
    date = models.DateField(db_index=True, help_text="Fecha del snapshot")
    
    # KPIs Principales
    total_orders = models.IntegerField(default=0, help_text="Total de pedidos")
    total_guides = models.IntegerField(default=0, help_text="Total de guías")
    products_sold = models.IntegerField(default=0, help_text="Total de productos vendidos")
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Ingresos totales")
    total_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Ganancia total")
    confirmation_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% de confirmación")
    cancellation_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% de cancelación")
    
    # Desglose por Estado
    delivered_count = models.IntegerField(default=0, help_text="Órdenes entregadas")
    returns_count = models.IntegerField(default=0, help_text="Órdenes devueltas")
    cancelled_count = models.IntegerField(default=0, help_text="Órdenes canceladas")
    in_transit_count = models.IntegerField(default=0, help_text="Órdenes en tránsito")
    in_warehouse_count = models.IntegerField(default=0, help_text="Órdenes en bodega")
    recollections_count = models.IntegerField(default=0, help_text="Órdenes en recaudo")
    
    # Finanzas Generales
    projected_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Ingresos proyectados (confirmados)")
    recovered_valuation = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Valoración recuperada de cancelados")
    projected_profit_bps = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Utilidad proyectada (BPS)")
    net_profit_real = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Ganancia neta real (entregados)")
    
    # Métricas de Rendimiento
    delivery_effectiveness_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% Efectividad de entrega")
    global_returns_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% Devoluciones global")
    annulation_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% Anulación")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_daily_snapshots'
        verbose_name = "Snapshot Diario Analytics"
        verbose_name_plural = "Snapshots Diarios Analytics"
        unique_together = [('user', 'date')]
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['user', '-date']),
        ]
        ordering = ['-date']
    
    def __str__(self):
        return f"Analytics {self.user.username} - {self.date}"


class AnalyticsCarrierDaily(models.Model):
    """
    Métricas diarias por transportadora por usuario.
    Almacena métricas detalladas de rendimiento por transportadora.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='analytics_carrier_daily'
    )
    date = models.DateField(db_index=True, help_text="Fecha del snapshot")
    carrier = models.CharField(max_length=100, db_index=True, help_text="Nombre de la transportadora")
    
    approved_count = models.IntegerField(default=0, help_text="Total aprobados")
    delivered_count = models.IntegerField(default=0, help_text="Entregados")
    returns_count = models.IntegerField(default=0, help_text="Devoluciones")
    cancelled_count = models.IntegerField(default=0, help_text="Cancelados")
    recollections_count = models.IntegerField(default=0, help_text="Recaudos")
    in_transit_count = models.IntegerField(default=0, help_text="En tránsito")
    times_count = models.IntegerField(default=0, help_text="Con tiempos (retrasos)")
    times_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% Tiempos")
    sales_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Monto de ventas")
    sales_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% Ventas del total")
    effectiveness_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% Efectividad")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_carrier_daily'
        verbose_name = "Analytics Transportadora Diario"
        verbose_name_plural = "Analytics Transportadoras Diarios"
        unique_together = [('user', 'date', 'carrier')]
        indexes = [
            models.Index(fields=['user', 'date', 'carrier']),
            models.Index(fields=['user', 'carrier']),
            models.Index(fields=['user', '-date']),
        ]
        ordering = ['-date', '-sales_amount']
    
    def __str__(self):
        return f"{self.carrier} - {self.user.username} - {self.date}"


class AnalyticsProductDaily(models.Model):
    """
    Métricas diarias por producto por usuario.
    Almacena métricas de rentabilidad por producto.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='analytics_product_daily'
    )
    date = models.DateField(db_index=True, help_text="Fecha del snapshot")
    product_name = models.TextField(db_index=True, help_text="Nombre del producto")
    
    sales_count = models.IntegerField(default=0, help_text="Cantidad de ventas")
    profit_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Utilidad total")
    margin_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% Margen")
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% Descuento")
    sale_value = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Valor de venta")
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Utilidad bruta")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_product_daily'
        verbose_name = "Analytics Producto Diario"
        verbose_name_plural = "Analytics Productos Diarios"
        unique_together = [('user', 'date', 'product_name')]
        indexes = [
            models.Index(fields=['user', 'date', 'product_name']),
            models.Index(fields=['user', 'product_name']),
            models.Index(fields=['user', '-date']),
        ]
        ordering = ['-date', '-gross_profit']
    
    def __str__(self):
        return f"{self.product_name[:50]} - {self.user.username} - {self.date}"


class AnalyticsCarrierReports(models.Model):
    """
    Conteo de reportes generados por transportadora.
    Almacena información sobre qué transportadoras han sido más reportadas.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='analytics_carrier_reports'
    )
    carrier = models.CharField(max_length=100, db_index=True, help_text="Nombre de la transportadora")
    report_date = models.DateField(db_index=True, help_text="Fecha del reporte")
    reports_count = models.IntegerField(default=0, help_text="Cantidad de reportes generados")
    last_reported_at = models.DateTimeField(null=True, blank=True, help_text="Última vez que se reportó")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_carrier_reports'
        verbose_name = "Analytics Reportes Transportadora"
        verbose_name_plural = "Analytics Reportes Transportadoras"
        unique_together = [('user', 'carrier', 'report_date')]
        indexes = [
            models.Index(fields=['user', 'carrier', 'report_date']),
            models.Index(fields=['user', 'carrier']),
            models.Index(fields=['user', '-report_date']),
        ]
        ordering = ['-report_date', '-reports_count']
    
    def __str__(self):
        return f"{self.carrier} - {self.user.username} - {self.report_date} ({self.reports_count} reportes)"


class AnalyticsStatusBreakdown(models.Model):
    """
    Desglose de órdenes por estado.
    Almacena conteo y valores por estado para análisis detallado.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='analytics_status_breakdown'
    )
    date = models.DateField(db_index=True, help_text="Fecha del snapshot")
    status = models.CharField(max_length=100, db_index=True, help_text="Estado de la orden")
    orders_count = models.IntegerField(default=0, help_text="Cantidad de órdenes")
    total_value = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Valor total")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_status_breakdown'
        verbose_name = "Analytics Desglose Estado"
        verbose_name_plural = "Analytics Desglose Estados"
        unique_together = [('user', 'date', 'status')]
        indexes = [
            models.Index(fields=['user', 'date', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', '-date']),
        ]
        ordering = ['-date', '-orders_count']
    
    def __str__(self):
        return f"{self.status} - {self.user.username} - {self.date} ({self.orders_count} órdenes)"
