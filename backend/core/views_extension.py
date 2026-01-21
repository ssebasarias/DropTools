
from django.contrib.auth.models import User

class ReporterConfigView(APIView):
    """
    Gestiona la configuración del Reporter (Credenciales de Dropi).
    """
    def get(self, request):
        # Fallback para usuario único en desarrollo
        user = request.user
        if not user or not user.is_authenticated:
            user = User.objects.first()
            if not user:
                return Response({"error": "No active user found. Please create a superuser."}, status=400)

        # Obtener o crear perfil
        try:
            profile = user.profile
        except Exception: # UserProfile.DoesNotExist might not be available if import failed previously
            try:
                profile = UserProfile.objects.create(user=user)
            except Exception as e:
                # Si UserProfile no está importado? (imported from .models above)
                from .models import UserProfile
                profile, _ = UserProfile.objects.get_or_create(user=user)

        return Response({
            "email": profile.dropi_email or "",
            "password": profile.dropi_password or "",
            "executionTime": "08:00" # Placeholder, no persistido aún
        })

    def post(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            user = User.objects.first()
            if not user:
                 return Response({"error": "No active user found"}, status=400)
             
        try:
            from .models import UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            profile.dropi_email = request.data.get('email')
            profile.dropi_password = request.data.get('password')
            profile.save()
            
            return Response({"status": "success", "message": "Credentials updated"})
        except Exception as e:
            return Response({"error": str(e)}, status=500)
