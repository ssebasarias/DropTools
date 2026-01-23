from __future__ import annotations

from dataclasses import dataclass

from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Admin-only permission based on User.role == 'ADMIN'.
    """

    message = "Acceso restringido: se requiere rol ADMIN."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        # Usar User directamente (ahora todo está en la tabla users)
        return bool(user.role == "ADMIN" or user.is_superuser)


def MinSubscriptionTier(required_tier: str):
    """
    Factory that returns a Permission Class enforcing a minimum subscription tier.
    Usage: permission_classes = [MinSubscriptionTier('BRONZE')]
    """
    class MinTierPermission(BasePermission):
        message = "Tu suscripción no tiene acceso a esta funcionalidad."
        
        _ORDER = {
            "BRONZE": 10,
            "SILVER": 20,
            "GOLD": 30,
            "PLATINUM": 40,
        }

        def has_permission(self, request, view):
            user = getattr(request, "user", None)
            if not user or not user.is_authenticated:
                return False

            # Usar User directamente (ahora todo está en la tabla users)
            if user.role == "ADMIN" or user.is_superuser:
                return True

            # Subscription must be active to use paid features
            if not user.subscription_active:
                return False

            have = self._ORDER.get(user.subscription_tier, 0)
            need = self._ORDER.get(required_tier, 0)
            return have >= need

    return MinTierPermission

