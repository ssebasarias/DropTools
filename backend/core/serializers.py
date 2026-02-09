# -*- coding: utf-8 -*-
"""
Django REST Framework Serializers
Serialización estandarizada de modelos para respuestas API
"""
from rest_framework import serializers
from .models import (
    Product, 
    Supplier, 
    UniqueProductCluster, 
    Category,
    ProductClusterMembership,
    ProductEmbedding
)


class SupplierSerializer(serializers.ModelSerializer):
    """Serializer para proveedores"""
    class Meta:
        model = Supplier
        fields = ['supplier_id', 'name', 'store_name', 'plan_name', 'is_verified']


class CategorySerializer(serializers.ModelSerializer):
    """Serializer para categorías"""
    class Meta:
        model = Category
        fields = ['id', 'name']


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer para productos
    Incluye información de proveedor embebido
    """
    supplier = SupplierSerializer(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'product_id',
            'sku',
            'title',
            'description',
            'sale_price',
            'suggested_price',
            'product_type',
            'url_image_s3',
            'is_active',
            'supplier',
            'created_at',
            'updated_at'
        ]


class ProductLightSerializer(serializers.ModelSerializer):
    """
    Versión ligera del ProductSerializer
    Para listados donde no se necesitan todos los campos
    """
    class Meta:
        model = Product
        fields = [
            'product_id',
            'title',
            'sale_price',
            'url_image_s3',
            'product_type'
        ]


class ClusterSerializer(serializers.ModelSerializer):
    """
    Serializer para clusters de productos únicos
    Incluye producto representante embebido
    """
    representative = ProductLightSerializer(source='representative_product', read_only=True)
    representative_supplier = serializers.SerializerMethodField()
    
    class Meta:
        model = UniqueProductCluster
        fields = [
            'cluster_id',
            'representative',
            'representative_supplier',
            'total_competitors',
            'average_price',
            'saturation_score',
            'created_at',
            'updated_at'
        ]
    
    def get_representative_supplier(self, obj):
        """Obtener información del proveedor del representante"""
        if obj.representative_product and obj.representative_product.supplier:
            return SupplierSerializer(obj.representative_product.supplier).data
        return None


class ClusterMembershipSerializer(serializers.ModelSerializer):
    """Serializer para membresías de productos en clusters"""
    product = ProductLightSerializer(read_only=True)
    cluster = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = ProductClusterMembership
        fields = [
            'product',
            'cluster',
            'match_confidence',
            'match_method'
        ]


class ProductEmbeddingSerializer(serializers.ModelSerializer):
    """
    Serializer para embeddings de productos
    Solo metadatos, no el vector completo (muy pesado).
    El modelo solo tiene embedding_visual y processed_at.
    """
    has_visual_embedding = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductEmbedding
        fields = [
            'product_id',
            'has_visual_embedding',
            'processed_at'
        ]
    
    def get_has_visual_embedding(self, obj):
        return obj.embedding_visual is not None


# Serializers especializados para diferentes views

class GoldMineProductSerializer(serializers.Serializer):
    """
    Serializer especializado para Gold Mine
    No vinculado a modelo (Serializer genérico)
    """
    id = serializers.IntegerField()
    title = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    image = serializers.URLField(allow_null=True)
    competitors = serializers.IntegerField()
    profit_margin = serializers.FloatField(allow_null=True)
    supplier = serializers.CharField()
    cluster_id = serializers.IntegerField(allow_null=True)
    badge = serializers.CharField(allow_null=True)


class DashboardTacticalOpportunitySerializer(serializers.Serializer):
    """Serializer para oportunidades tácticas del dashboard"""
    id = serializers.IntegerField()
    title = serializers.CharField()
    image = serializers.URLField(allow_null=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    margin = serializers.FloatField(allow_null=True)
    competitors = serializers.IntegerField()
    supplier = serializers.CharField()
    badge = serializers.CharField()


# -----------------------------------------------------------------------------
# Google OAuth Authentication
# -----------------------------------------------------------------------------

from .models import User


class GoogleAuthSerializer(serializers.Serializer):
    """
    Serializer para autenticación con Google OAuth.
    Recibe el token de Google y valida la identidad del usuario.
    """
    token = serializers.CharField(required=True, help_text="ID token de Google")
    
    def validate_token(self, value):
        """
        Valida el token de Google y extrae la información del usuario.
        """
        try:
            from django.conf import settings
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests

            # Verificar el token con Google
            idinfo = id_token.verify_oauth2_token(
                value, 
                google_requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )
            
            # Verificar que el token es de Google
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise serializers.ValidationError('Token inválido: emisor no reconocido')
            
            # Guardar la info del usuario en el contexto
            self.context['google_user_info'] = {
                'email': idinfo.get('email'),
                'name': idinfo.get('name'),
                'given_name': idinfo.get('given_name'),
                'family_name': idinfo.get('family_name'),
                'picture': idinfo.get('picture'),
                'email_verified': idinfo.get('email_verified', False),
                'google_id': idinfo.get('sub'),
            }
            
            return value
            
        except ValueError as e:
            raise serializers.ValidationError(f'Token inválido: {str(e)}')
    
    def create(self, validated_data):
        """
        Crea o actualiza el usuario basado en la información de Google.
        """
        google_info = self.context['google_user_info']
        
        # Email verificado por Google (algunos flujos no envían el claim; si tenemos email lo aceptamos)
        email = google_info.get('email')
        if not email:
            raise serializers.ValidationError('No se pudo obtener el email de la cuenta de Google')
        if google_info.get('email_verified') is False:
            raise serializers.ValidationError('El email de Google no está verificado')
        
        # Buscar o crear usuario (usuarios Google sin password local; solo login con Google)
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,  # Usar email como username
                'full_name': google_info.get('name', ''),
                'is_active': True,
                'subscription_tier': User.TIER_BRONZE,
                'subscription_active': True,
            }
        )
        if created:
            user.set_unusable_password()  # Obligatorio: AbstractUser exige password; OAuth no usa password local
            user.save(update_fields=['password'])

        # Si el usuario ya existía, actualizar su nombre si está vacío
        if not created and not user.full_name:
            user.full_name = google_info.get('name', '')
            user.save()

        return user


# -----------------------------------------------------------------------------
# Reporter slot system
# -----------------------------------------------------------------------------

from .models import ReporterHourSlot, ReporterReservation, ReporterRun, ReporterRunUser


class ReporterSlotSerializer(serializers.ModelSerializer):
    """Slot horario con capacidad por peso (used_points, capacity_points, available)."""
    used_points = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()
    hour_label = serializers.SerializerMethodField()

    class Meta:
        model = ReporterHourSlot
        fields = ['id', 'hour', 'hour_label', 'capacity_points', 'used_points', 'available']

    def get_used_points(self, obj):
        return getattr(obj, 'used_points', None) or 0

    def get_available(self, obj):
        used = getattr(obj, 'used_points', None) or 0
        cap = getattr(obj, 'capacity_points', None) or 6
        return used < cap

    def get_hour_label(self, obj):
        return f"{obj.hour:02d}:00"


class ReporterReservationSerializer(serializers.ModelSerializer):
    slot = ReporterSlotSerializer(read_only=True)
    slot_id = serializers.PrimaryKeyRelatedField(
        queryset=ReporterHourSlot.objects.all(),
        source='slot',
        write_only=True
    )

    class Meta:
        model = ReporterReservation
        fields = [
            'id', 'slot', 'slot_id', 'monthly_orders_estimate', 'calculated_weight',
            'estimated_pending_orders', 'created_at', 'updated_at'
        ]
        read_only_fields = ['calculated_weight', 'estimated_pending_orders', 'created_at', 'updated_at']


class ReporterRunSerializer(serializers.ModelSerializer):
    slot_hour = serializers.SerializerMethodField()

    class Meta:
        model = ReporterRun
        fields = [
            'id', 'slot', 'slot_hour', 'scheduled_at', 'started_at', 'finished_at',
            'status', 'created_at'
        ]

    def get_slot_hour(self, obj):
        return obj.slot.hour if obj.slot_id else None


class ReporterRunProgressSerializer(serializers.Serializer):
    """Progreso de una Run por usuario (para GET /api/reporter/runs/<id>/progress/)."""
    run_id = serializers.IntegerField()
    run_status = serializers.CharField()
    scheduled_at = serializers.DateTimeField()
    users = serializers.ListField(child=serializers.DictField())
