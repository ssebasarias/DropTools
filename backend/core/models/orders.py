from django.db import models
from django.conf import settings
from .user import User


class OrderReport(models.Model):
    """
    Tabla de reportes de órdenes generados por el bot reporter.
    Reemplaza el sistema de checkpoints CSV por una base de datos más eficiente.
    """
    
    STATUS_CHOICES = [
        ('proximo_a_reportar', 'Próximo a Reportar'),
        ('reportado', 'Reportado'),
        ('error', 'Error'),
        ('no_encontrado', 'No Encontrado'),
        ('already_has_case', 'Ya Tiene Caso'),
        ('cannot_generate_yet', 'No Se Puede Generar Aún'),
        ('in_movement', 'En Movimiento'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='order_reports')
    order_phone = models.CharField(max_length=50, db_index=True, help_text="Número de teléfono de la orden")
    order_id = models.CharField(max_length=100, null=True, blank=True, help_text="ID de la orden en Dropi")
    tracking_number = models.CharField(max_length=100, null=True, blank=True, help_text="Número de guía / Tracking")
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='proximo_a_reportar')
    report_generated = models.BooleanField(default=False, help_text="True si el reporte se generó exitosamente")
    
    # Información adicional de la orden
    customer_name = models.CharField(max_length=255, null=True, blank=True, help_text="Nombre del cliente")
    product_name = models.TextField(null=True, blank=True, help_text="Nombre del producto vinculado a la orden")
    order_state = models.CharField(max_length=100, null=True, blank=True, help_text="Estado actual de la orden en Dropi")
    days_since_order = models.IntegerField(null=True, blank=True, help_text="Días transcurridos desde la orden (del CSV)")
    
    # Control de tiempos
    next_attempt_time = models.DateTimeField(null=True, blank=True, help_text="Próximo intento (para estados que requieren espera)")
    reported_at = models.DateTimeField(
        null=True, blank=True, db_index=True,
        help_text="Fecha y hora en que se generó el reporte exitosamente (status=reportado). Para control y KPIs."
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'order_reports'
        indexes = [
            models.Index(fields=['user', 'order_phone']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'report_generated']),
            models.Index(fields=['order_phone']),  # Para búsquedas rápidas
            models.Index(fields=['next_attempt_time']),  # Para filtrar por tiempo
        ]
        # Un usuario no puede tener múltiples reportes activos para la misma orden
        # (pero puede tener múltiples intentos históricos si falla)
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


class ReportBatch(models.Model):
    """
    Representa un lote de descarga de reportes de Dropi.
    Reemplaza la dependencia de carpetas/archivos físicos y permite trazabilidad total.
    """
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='report_batches')
    account_email = models.EmailField(max_length=255, help_text="Email de la cuenta Dropi de donde vino este reporte")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default="SUCCESS")  # SUCCESS, FAILED, PROCESSING
    
    # Metadata opcional del lote
    total_records = models.IntegerField(default=0, help_text="Total de filas leídas del Excel")

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
    Una 'foto' de una orden en un momento específico (traída de un ReportBatch).
    Contiene la data cruda del Excel de Dropi mapeada a columnas estructuradas.
    Permite comparar estados entre Batches para detectar 'Sin Movimiento'.
    """
    id = models.BigAutoField(primary_key=True)
    batch = models.ForeignKey(ReportBatch, on_delete=models.CASCADE, related_name='snapshots')
    
    # IDs e Identificadores Clave
    dropi_order_id = models.CharField(max_length=100, db_index=True, help_text="Columna: ID")
    shopify_order_id = models.CharField(max_length=100, null=True, blank=True, help_text="Columna: NUMERO DE PEDIDO DE TIENDA")
    guide_number = models.CharField(max_length=100, null=True, blank=True, help_text="Columna: NÚMERO GUIA")
    
    # Estado y Logística
    current_status = models.CharField(max_length=100, db_index=True, help_text="Columna: ESTATUS")
    carrier = models.CharField(max_length=100, null=True, blank=True, help_text="Columna: TRANSPORTADORA")
    
    # Cliente
    customer_name = models.CharField(max_length=255, null=True, blank=True, help_text="Columna: NOMBRE CLIENTE")
    customer_phone = models.CharField(max_length=50, db_index=True, null=True, blank=True, help_text="Columna: TELÉFONO")
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
            models.Index(fields=['batch', 'current_status']),  # Optimiza queries de comparación
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
