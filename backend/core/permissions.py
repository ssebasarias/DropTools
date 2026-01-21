from __future__ import annotations

from dataclasses import dataclass

from rest_framework.permissions import BasePermission


def _get_profile(user):
    """
    Safe profile fetch. Returns None if missing.
    """
    try:
        return getattr(user, "profile", None)
    except Exception:
        return None


class IsAdminRole(BasePermission):
    """
    Admin-only permission based on UserProfile.role == 'ADMIN'.
    """

    message = "Acceso restringido: se requiere rol ADMIN."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        profile = _get_profile(user)
        return bool(profile and profile.role == "ADMIN")


@dataclass(frozen=True)
class MinSubscriptionTier(BasePermission):
    """
    Requires a minimum subscription tier.
    Admin role bypasses tier checks.
    """

    required: str
    message: str = "Tu suscripción no tiene acceso a esta funcionalidad."

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

        profile = _get_profile(user)
        if not profile:
            return False

        if profile.role == "ADMIN":
            return True

        # Subscription must be active to use paid features (payments not implemented yet).
        if not getattr(profile, "subscription_active", False):
            return False

        have = self._ORDER.get(getattr(profile, "subscription_tier", None), 0)
        need = self._ORDER.get(self.required, 0)
        return have >= need

