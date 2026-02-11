# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..models import User
from ..permissions import IsAdminRole


class AdminUsersView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        users = User.objects.all().order_by("id")
        rows = []
        for u in users:
            # Usar User directamente (ahora todo está en la tabla users)
            rows.append(
                {
                    "id": u.id,
                    "email": u.email,
                    "username": u.username,
                    "is_active": u.is_active,
                    "profile": {
                        "full_name": u.full_name,
                        "role": u.role,
                        "subscription_tier": u.subscription_tier,
                        "subscription_active": u.subscription_active,
                    },
                }
            )
        return Response({"users": rows}, status=status.HTTP_200_OK)


class AdminSetUserSubscriptionView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, user_id: int):
        target = User.objects.filter(id=user_id).first()
        if not target:
            return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        tier = (request.data.get("subscription_tier") or "").upper().strip()
        active = request.data.get("subscription_active")

        valid_tiers = {"BRONZE", "SILVER", "GOLD", "PLATINUM"}
        if tier and tier not in valid_tiers:
            return Response({"error": "Tier inválido"}, status=status.HTTP_400_BAD_REQUEST)

        # Actualizar directamente en User (ahora todo está en la tabla users)
        if tier:
            target.subscription_tier = tier
        if active is not None:
            target.subscription_active = bool(active)
        target.save()

        return Response(
            {
                "status": "ok",
                "user_id": target.id,
                "subscription_tier": target.subscription_tier,
                "subscription_active": target.subscription_active,
            },
            status=status.HTTP_200_OK,
        )
