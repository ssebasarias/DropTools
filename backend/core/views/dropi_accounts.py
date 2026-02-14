# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ..permissions import MinSubscriptionTier


class DropiAccountsView(APIView):
    """
    Gestiona la cuenta Dropi del usuario (ahora está en la tabla users)
    Nota: Ahora cada usuario tiene solo UNA cuenta Dropi (dropi_email y dropi_password)
    """
    permission_classes = [IsAuthenticated, MinSubscriptionTier("BRONZE")]

    def get(self, request):
        """Retorna la cuenta Dropi del usuario actual"""
        user = request.user
        
        # Retornar la cuenta Dropi del usuario (ahora está en User)
        accounts = []
        if user.dropi_email:
            accounts.append({
                "id": user.id,  # Usar el ID del usuario
                "label": "reporter",  # Label fijo para compatibilidad
                "email": user.dropi_email,
                "is_default": True  # Siempre es default porque solo hay una
            })
        
        return Response(
            {"accounts": accounts},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        """Actualiza la cuenta Dropi del usuario"""
        user = request.user
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""

        if not email or not password:
            return Response({"error": "email y password son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        # Actualizar dropi_email y dropi_password en User
        user.dropi_email = email
        user.set_dropi_password_plain(password)
        user.save()
        
        return Response(
            {
                "account": {
                    "id": user.id,
                    "label": "reporter",
                    "email": user.dropi_email,
                    "is_default": True
                }
            },
            status=status.HTTP_201_CREATED,
        )


class DropiAccountSetDefaultView(APIView):
    """
    Marca una cuenta Dropi como default (ahora es un no-op porque solo hay una cuenta)
    Se mantiene por compatibilidad con el frontend
    """
    permission_classes = [IsAuthenticated, MinSubscriptionTier("BRONZE")]

    def post(self, request, account_id: int):
        """
        Como ahora solo hay una cuenta Dropi por usuario, esta vista simplemente retorna OK
        Se mantiene por compatibilidad con el frontend
        """
        user = request.user
        
        # Verificar que el account_id corresponda al usuario actual
        if account_id != user.id:
            return Response({"error": "Cuenta no encontrada"}, status=status.HTTP_404_NOT_FOUND)
        
        # Como solo hay una cuenta, siempre es default
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
