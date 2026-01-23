
from core.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import time as dt_time

class ReporterConfigView(APIView):
    """
    Gestiona la configuración del Reporter (Credenciales de Dropi).
    Ahora usa User directamente (tabla users unificada).
    """
    def get(self, request):
        # Require authentication (no insecure fallbacks)
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

        # Usar User directamente (ahora todo está en la tabla users)
        exec_time = user.execution_time
        return Response(
            {
                # Usar credenciales Dropi directamente del User
                "email": user.dropi_email or "",
                # No devolver password por seguridad
                "password": "",
                # Persisted schedule time (HH:MM). Default 08:00 if not set.
                "executionTime": exec_time.strftime("%H:%M") if exec_time else "08:00",
            }
        )

    def post(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
             
        try:
            # Actualizar credenciales Dropi directamente en User
            if "email" in request.data or "password" in request.data:
                email = request.data.get("email", "").strip()
                password = request.data.get("password", "").strip()
                
                if email:
                    user.dropi_email = email
                if password:
                    user.set_dropi_password_plain(password)

            # Actualizar schedule time HH:MM
            exec_time_str = request.data.get("executionTime") or request.data.get("execution_time")
            if exec_time_str is not None:
                exec_time_str = str(exec_time_str).strip()
                if exec_time_str == "":
                    user.execution_time = None
                else:
                    try:
                        hh, mm = exec_time_str.split(":")
                        user.execution_time = dt_time(hour=int(hh), minute=int(mm))
                    except Exception:
                        return Response(
                            {"error": "executionTime inválido. Usa formato HH:MM"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

            user.save()
            
            return Response(
                {
                    "status": "success",
                    "message": "Configuración actualizada",
                    "executionTime": user.execution_time.strftime("%H:%M") if user.execution_time else None,
                }
            )
        except Exception as e:
            return Response({"error": str(e)}, status=500)
