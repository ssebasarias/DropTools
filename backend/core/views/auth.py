# -*- coding: utf-8 -*-
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.throttling import ScopedRateThrottle
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import User
from ..services.auth_tokens import (
    TokenValidationError,
    consume_token,
    create_auth_token,
    validate_token,
)
from ..services.auth_email_service import send_password_reset_email, send_verify_email

logger = logging.getLogger(__name__)

VERIFY_EMAIL_EXPIRY_SECONDS = getattr(settings, "VERIFY_EMAIL_EXPIRY_SECONDS", 24 * 60 * 60)
RESET_PASSWORD_EXPIRY_SECONDS = getattr(settings, "RESET_PASSWORD_EXPIRY_SECONDS", 60 * 60)


def _serialize_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "subscription_tier": user.subscription_tier,
        "subscription_active": user.subscription_active,
        "full_name": user.full_name,
        "is_admin": bool(user.role == "ADMIN"),
        "email_verified": bool(user.email_verified),
    }


class AuthLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

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
        if user.has_usable_password() and not user.email_verified:
            return Response(
                {"error": "Debes verificar tu correo antes de iniciar sesión"},
                status=status.HTTP_403_FORBIDDEN,
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": _serialize_user(user),
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
        from rest_framework.serializers import ValidationError as DRFValidationError
        from ..serializers import GoogleAuthSerializer
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
                'user': _serialize_user(user),
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
                {'error': 'Error interno al autenticar con Google.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuthRegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        """
        Registro público:
        - Crea User + UserProfile (CLIENT + BRONZE por defecto)
        - No inicia sesión automáticamente
        - Envía correo de verificación
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
        user.email_verified = False
        user.email_verified_at = None
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

        try:
            verify_token = create_auth_token(
                user=user,
                purpose="verify_email",
                expires_in_seconds=VERIFY_EMAIL_EXPIRY_SECONDS,
            )
            send_verify_email(user, verify_token)
        except Exception as exc:
            logger.error("No se pudo enviar email de verificación para user_id=%s: %s", user.id, exc)

        return Response(
            {
                "detail": "Te enviamos un correo de verificación. Revisa tu bandeja de entrada.",
                "user": _serialize_user(user),
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "verify_email"

    def post(self, request):
        raw_token = (request.data.get("token") or "").strip()
        if not raw_token:
            return Response({"detail": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token_record = validate_token(raw_token, purpose="verify_email")
        except TokenValidationError as exc:
            if exc.code == "expired":
                return Response({"detail": "Token expirado."}, status=status.HTTP_410_GONE)
            if exc.code == "used":
                return Response({"detail": "Token ya utilizado."}, status=status.HTTP_409_CONFLICT)
            return Response({"detail": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)

        user = token_record.user
        with transaction.atomic():
            user.email_verified = True
            if not user.email_verified_at:
                user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified", "email_verified_at"])
            consume_token(token_record)

        return Response({"detail": "Email verificado correctamente."}, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_request"

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        # Respuesta uniforme para evitar enumeración de usuarios.
        generic_response = {
            "detail": "Si el email existe, enviaremos instrucciones para restablecer la contraseña."
        }
        if not email:
            return Response(generic_response, status=status.HTTP_200_OK)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(generic_response, status=status.HTTP_200_OK)

        try:
            reset_token = create_auth_token(
                user=user,
                purpose="reset_password",
                expires_in_seconds=RESET_PASSWORD_EXPIRY_SECONDS,
            )
            send_password_reset_email(user, reset_token)
        except Exception as exc:
            logger.error("Error enviando reset password para user_id=%s: %s", user.id, exc)
        return Response(generic_response, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_confirm"

    def post(self, request):
        raw_token = (request.data.get("token") or "").strip()
        new_password = request.data.get("new_password") or ""

        if not raw_token:
            return Response({"detail": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)
        if not new_password:
            return Response({"detail": "La nueva contraseña es requerida."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token_record = validate_token(raw_token, purpose="reset_password")
        except TokenValidationError as exc:
            if exc.code == "expired":
                return Response({"detail": "Token expirado."}, status=status.HTTP_410_GONE)
            if exc.code == "used":
                return Response({"detail": "Token ya utilizado."}, status=status.HTTP_409_CONFLICT)
            return Response({"detail": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)

        user = token_record.user
        try:
            validate_password(new_password, user=user)
        except ValidationError as exc:
            detail = exc.messages[0] if exc.messages else "Contraseña inválida."
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user.set_password(new_password)
            user.save(update_fields=["password"])
            consume_token(token_record)
            Token.objects.filter(user=user).delete()

        return Response({"detail": "Contraseña actualizada correctamente."}, status=status.HTTP_200_OK)


class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Usar User directamente (ahora todo está en la tabla users)
        user = request.user
        return Response(
            {
                "user": _serialize_user(user)
            },
            status=status.HTTP_200_OK,
        )
