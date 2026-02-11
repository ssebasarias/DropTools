# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.conf import settings
from ..models import User


class AuthLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password", "").strip()
        if not email or not password:
            return Response({"error": "email y password son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        # Permitimos login por email o username
        user_obj = User.objects.filter(email=email).first() or User.objects.filter(username=email).first()
        if not user_obj:
            return Response({"error": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)

        # Autenticar usando el username del usuario encontrado
        user = authenticate(request, username=user_obj.username, password=password)
        if not user:
            return Response({"error": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({"error": "Usuario inactivo"}, status=status.HTTP_403_FORBIDDEN)

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "subscription_tier": user.subscription_tier,
                    "subscription_active": user.subscription_active,
                    "full_name": user.full_name,
                    "is_admin": bool(user.role == "ADMIN"),
                },
            },
            status=status.HTTP_200_OK,
        )


class GoogleAuthView(APIView):
    """
    Endpoint para autenticación con Google OAuth.
    
    POST /api/auth/google/
    Body: { "token": "google_id_token" }
    
    Retorna:
    - user: Información del usuario
    - token: Token de autenticación de Django
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        import logging
        from rest_framework.serializers import ValidationError as DRFValidationError
        from ..serializers import GoogleAuthSerializer

        logger = logging.getLogger(__name__)
        serializer = GoogleAuthSerializer(data=request.data)

        if not serializer.is_valid():
            err_msg = serializer.errors.get('token', serializer.errors)
            if isinstance(err_msg, list):
                err_msg = err_msg[0] if err_msg else str(serializer.errors)
            return Response(
                {'error': err_msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'full_name': user.full_name,
                    'is_admin': user.is_admin(),
                    'subscription_tier': user.subscription_tier,
                    'subscription_active': user.subscription_active,
                }
            }, status=status.HTTP_200_OK)
        except DRFValidationError as e:
            detail = e.detail if hasattr(e, 'detail') else str(e)
            if isinstance(detail, list):
                detail = detail[0] if detail else str(detail)
            if isinstance(detail, dict):
                detail = str(detail)
            return Response({'error': detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Google auth 500: %s", e)
            return Response(
                {'error': f'Error al autenticar con Google: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuthRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Registro público:
        - Crea User + UserProfile (CLIENT + BRONZE por defecto)
        - Devuelve token para auto-login
        """
        full_name = (request.data.get("full_name") or request.data.get("name") or "").strip()
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""

        if not email or not password:
            return Response({"error": "email y password son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
            return Response({"error": "Este email ya está registrado"}, status=status.HTTP_400_BAD_REQUEST)

        # Use email as username (simple + consistent)
        user = User.objects.create_user(username=email, email=email, password=password)
        user.is_active = True
        # Configurar campos de perfil directamente en User
        user.full_name = full_name
        user.role = User.ROLE_CLIENT
        user.subscription_tier = User.TIER_BRONZE
        # En desarrollo (DEBUG): bronce activo por defecto para poder probar la app
        user.subscription_active = getattr(settings, 'DEBUG', False)
        user.save()

        # Asignar proxy disponible al nuevo usuario (si hay proxies configurados)
        try:
            from ..services.proxy_allocator_service import assign_proxy_to_user
            assign_proxy_to_user(user.id)
        except Exception:
            pass  # Registro exitoso aunque no haya proxy disponible

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "subscription_tier": user.subscription_tier,
                    "subscription_active": user.subscription_active,
                    "full_name": user.full_name,
                    "is_admin": bool(user.role == "ADMIN"),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Usar User directamente (ahora todo está en la tabla users)
        user = request.user
        return Response(
            {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "subscription_tier": user.subscription_tier,
                    "subscription_active": user.subscription_active,
                    "full_name": user.full_name,
                    "is_admin": bool(user.role == "ADMIN"),
                }
            },
            status=status.HTTP_200_OK,
        )
