from django.db import models
from django.conf import settings


def reporter_reservation_weight_from_orders(monthly_orders_estimate):
    """
    Peso según volumen de órdenes mensuales:
    Pequeño 0-2000 → 1, Mediano 2001-5000 → 2, Grande 5001-10000 → 3.
    Valores fuera de rango se acotan (>=10001 → 3, negativo → 1).
    """
    if monthly_orders_estimate is None or monthly_orders_estimate < 0:
        return 1
    n = min(int(monthly_orders_estimate), 10000)
    if n <= 2000:
        return 1
    if n <= 5000:
        return 2
    return 3


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
    range_size = models.PositiveIntegerField(default=50, help_text="Tamaño de cada rango de órdenes a reportar")
    slot_capacity = models.PositiveSmallIntegerField(
        default=6,
        help_text="Puntos de capacidad máximos por hora (suma de pesos de reservas)"
    )
    reporter_hour_start = models.PositiveSmallIntegerField(
        default=6,
        help_text="Hora inicio ventana reporter (0-23). Ej: 6 = 6:00"
    )
    reporter_hour_end = models.PositiveSmallIntegerField(
        default=18,
        help_text="Hora fin ventana reporter (0-23). Ej: 18 = horas 6-17 reservables"
    )
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
    hour: 0-23 (único). Capacidad por límites independientes por peso.
    """
    hour = models.PositiveSmallIntegerField(unique=True, help_text="Hora del día (0-23)")
    max_users = models.PositiveIntegerField(default=10, help_text="(Legacy) Ya no se usa; disponibilidad por capacity_points")
    capacity_points = models.PositiveSmallIntegerField(
        default=6,
        help_text="(Deprecated) Puntos de capacidad máximos en esta hora (suma de calculated_weight). Usar límites por peso en su lugar."
    )
    max_users_weight_3 = models.PositiveSmallIntegerField(
        default=2,
        help_text="Máximo número de usuarios de peso 3 (grandes) permitidos en esta hora"
    )
    max_users_weight_2 = models.PositiveSmallIntegerField(
        default=2,
        help_text="Máximo número de usuarios de peso 2 (medianos) permitidos en esta hora"
    )
    max_users_weight_1 = models.PositiveSmallIntegerField(
        default=2,
        help_text="Máximo número de usuarios de peso 1 (pequeños) permitidos en esta hora"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reporter_hour_slots'
        verbose_name = "Slot horario Reporter"
        verbose_name_plural = "Slots horarios Reporter"
        ordering = ['hour']

    def __str__(self):
        return f"{self.hour:02d}:00 (peso3:{self.max_users_weight_3}, peso2:{self.max_users_weight_2}, peso1:{self.max_users_weight_1})"

    def count_users_by_weight(self, weight, exclude_user=None):
        """
        Cuenta cuántos usuarios de un peso específico están asignados a este slot.
        
        Args:
            weight: Peso a contar (1, 2 o 3)
            exclude_user: Usuario a excluir del conteo (útil para actualizaciones)
        
        Returns:
            int: Número de usuarios de ese peso
        """
        from django.db.models import Q
        query = Q(calculated_weight=weight)
        if exclude_user:
            query &= ~Q(user=exclude_user)
        return self.reservations.filter(query).count()

    def can_accept_user_weight(self, weight, exclude_user=None):
        """
        Verifica si este slot puede aceptar un usuario del peso especificado.
        
        Args:
            weight: Peso del usuario (1, 2 o 3)
            exclude_user: Usuario a excluir del conteo (útil para actualizaciones)
        
        Returns:
            bool: True si puede aceptar, False si está lleno
        """
        if weight == 3:
            max_allowed = self.max_users_weight_3
        elif weight == 2:
            max_allowed = self.max_users_weight_2
        elif weight == 1:
            max_allowed = self.max_users_weight_1
        else:
            return False
        
        current_count = self.count_users_by_weight(weight, exclude_user=exclude_user)
        return current_count < max_allowed

    def get_available_capacity_by_weight(self, weight, exclude_user=None):
        """
        Retorna cuántos usuarios del peso especificado pueden entrar aún.
        
        Args:
            weight: Peso del usuario (1, 2 o 3)
            exclude_user: Usuario a excluir del conteo (útil para actualizaciones)
        
        Returns:
            int: Número de espacios disponibles para ese peso
        """
        if weight == 3:
            max_allowed = self.max_users_weight_3
        elif weight == 2:
            max_allowed = self.max_users_weight_2
        elif weight == 1:
            max_allowed = self.max_users_weight_1
        else:
            return 0
        
        current_count = self.count_users_by_weight(weight, exclude_user=exclude_user)
        return max(0, max_allowed - current_count)


def assign_best_available_slot(user, monthly_orders_estimate):
    """
    Asigna automáticamente el primer slot disponible (por hora) para un usuario.
    
    Algoritmo (first-fit por hora con límites por peso):
    1. Calcula el peso del usuario según sus órdenes mensuales.
    2. Obtiene los slots en la ventana configurada (6am-6pm por defecto), ordenados por hora.
    3. Para cada slot, verifica el límite específico del peso del usuario:
       - Peso 3: verifica si hay menos de max_users_weight_3 usuarios de peso 3
       - Peso 2: verifica si hay menos de max_users_weight_2 usuarios de peso 2
       - Peso 1: verifica si hay menos de max_users_weight_1 usuarios de peso 1
    4. Asigna el PRIMER slot que tenga espacio para ese peso específico.
    5. Si el usuario ya tiene reserva en un slot, se excluye del conteo (actualización).
    
    Args:
        user: Usuario a asignar
        monthly_orders_estimate: Órdenes mensuales estimadas del usuario
    
    Returns:
        ReporterHourSlot: El slot asignado
    
    Raises:
        ValueError: Si no hay slots disponibles con suficiente capacidad para ese peso
    """
    user_weight = reporter_reservation_weight_from_orders(monthly_orders_estimate)
    
    # Validar peso
    if user_weight not in [1, 2, 3]:
        raise ValueError(f"Peso inválido: {user_weight}. Debe ser 1, 2 o 3.")
    
    # Obtener configuración de ventana horaria
    config = ReporterSlotConfig.objects.first()
    hour_start = getattr(config, 'reporter_hour_start', 6) if config else 6
    hour_end = getattr(config, 'reporter_hour_end', 18) if config else 18
    
    # Slots en la ventana, ordenados por hora (primera hora primero)
    slots = ReporterHourSlot.objects.filter(
        hour__gte=hour_start,
        hour__lt=hour_end
    ).order_by('hour')
    
    # Primer slot (por hora) que tenga espacio para el peso específico del usuario
    for slot in slots:
        # Verificar si el slot puede aceptar un usuario de este peso
        # Si el usuario ya tiene reserva en este slot, se excluye del conteo
        if slot.can_accept_user_weight(user_weight, exclude_user=user):
            return slot
    
    # Mensaje de error descriptivo según el peso
    weight_labels = {1: "pequeño (peso 1)", 2: "mediano (peso 2)", 3: "grande (peso 3)"}
    weight_label = weight_labels.get(user_weight, f"peso {user_weight}")
    
    raise ValueError(
        f"No hay slots disponibles con espacio para usuarios de {weight_label}. "
        f"Todas las horas en la ventana configurada ({hour_start:02d}:00 - {hour_end:02d}:00) "
        f"están llenas para tu nivel de volumen. Contacta al administrador."
    )


class ReporterReservation(models.Model):
    """
    Reserva de un usuario en una hora diaria.
    Un usuario solo puede tener una reserva (una hora).
    Peso por volumen: pequeño 0-2000→1, mediano 2001-5000→2, grande 5001-10000→3.
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
    calculated_weight = models.PositiveSmallIntegerField(
        default=1,
        help_text="Peso por volumen: 1 pequeño, 2 mediano, 3 grande (calculado al guardar)"
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
        return f"{self.user.username} → {self.slot.hour:02d}:00 (peso {self.calculated_weight})"

    def save(self, *args, **kwargs):
        config = ReporterSlotConfig.objects.first()
        factor = float(config.estimated_pending_factor) if config else 0.08
        self.estimated_pending_orders = self.monthly_orders_estimate * factor
        self.calculated_weight = reporter_reservation_weight_from_orders(self.monthly_orders_estimate)
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
