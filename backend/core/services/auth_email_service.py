from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail


def _build_frontend_link(path: str, token: str):
    base = getattr(settings, "FRONTEND_BASE_URL", "").rstrip("/")
    query = urlencode({"token": token})
    return f"{base}{path}?{query}"


def send_verify_email(user, token: str):
    verify_link = _build_frontend_link("/verify-email", token)
    subject = "Verifica tu correo en DropTools"
    message = (
        f"Hola {user.full_name or user.username},\n\n"
        "Gracias por registrarte en DropTools.\n"
        "Para activar tu cuenta, confirma tu correo con este enlace:\n\n"
        f"{verify_link}\n\n"
        "Este enlace expira en 24 horas.\n"
        "Si no creaste esta cuenta, puedes ignorar este mensaje."
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_password_reset_email(user, token: str):
    reset_link = _build_frontend_link("/reset-password", token)
    subject = "Restablece tu contraseña de DropTools"
    message = (
        f"Hola {user.full_name or user.username},\n\n"
        "Recibimos una solicitud para restablecer tu contraseña.\n"
        "Usa este enlace para definir una nueva contraseña:\n\n"
        f"{reset_link}\n\n"
        "Este enlace expira en 1 hora y solo se puede usar una vez.\n"
        "Si no solicitaste este cambio, ignora este mensaje."
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
