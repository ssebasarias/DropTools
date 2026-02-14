# -*- coding: utf-8 -*-
"""
Serializers para autenticación
"""
from rest_framework import serializers
from django.utils import timezone
from ..models import User


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
                'email_verified': True,
                'email_verified_at': timezone.now(),
                'subscription_tier': User.TIER_BRONZE,
                'subscription_active': True,
            }
        )
        if created:
            user.set_unusable_password()  # Obligatorio: AbstractUser exige password; OAuth no usa password local
            user.save(update_fields=['password'])

        # Si el usuario ya existía, actualizar su nombre si está vacío
        if not created:
            changed = False
            if not user.full_name:
                user.full_name = google_info.get('name', '')
                changed = True
            if not user.email_verified:
                user.email_verified = True
                user.email_verified_at = timezone.now()
                changed = True
            if changed:
                user.save(update_fields=['full_name', 'email_verified', 'email_verified_at'])

        return user
