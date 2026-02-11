from django.contrib import admin
from django.utils import timezone
from .models import ProxyIP, UserProxyAssignment
from .services.proxy_allocator_service import mark_proxy_blocked


@admin.action(description='Marcar proxies seleccionados como bloqueados')
def mark_proxies_blocked(modeladmin, request, queryset):
    """Acción para marcar múltiples proxies como bloqueados."""
    count = 0
    for proxy in queryset.filter(status=ProxyIP.STATUS_ACTIVE):
        try:
            mark_proxy_blocked(proxy.id, reason="Marcado manualmente desde admin")
            count += 1
        except Exception as e:
            modeladmin.message_user(request, f"Error al marcar proxy {proxy.id}: {e}", level='ERROR')
    modeladmin.message_user(request, f"{count} proxy(s) marcado(s) como bloqueado(s).")


@admin.action(description='Desbloquear proxies seleccionados')
def unblock_proxies(modeladmin, request, queryset):
    """Acción para desbloquear múltiples proxies."""
    count = queryset.filter(status=ProxyIP.STATUS_BLOCKED).update(
        status=ProxyIP.STATUS_ACTIVE,
        blocked_at=None,
        block_reason=None
    )
    modeladmin.message_user(request, f"{count} proxy(s) desbloqueado(s).")


@admin.register(ProxyIP)
class ProxyIPAdmin(admin.ModelAdmin):
    list_display = ('id', 'ip', 'port', 'max_accounts', 'status', 'blocked_at', 'created_at')
    list_filter = ('status', 'created_at', 'blocked_at')
    search_fields = ('ip', 'block_reason')
    readonly_fields = ('created_at', 'updated_at', 'blocked_at')
    actions = [mark_proxies_blocked, unblock_proxies]
    
    fieldsets = (
        ('Información básica', {
            'fields': ('ip', 'port', 'username', 'password_encrypted', 'max_accounts', 'status')
        }),
        ('Información de bloqueo', {
            'fields': ('blocked_at', 'block_reason'),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserProxyAssignment)
class UserProxyAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'proxy', 'proxy_status', 'assigned_at', 'last_used_at')
    list_filter = ('proxy', 'proxy__status', 'assigned_at')
    search_fields = ('user__email', 'user__username', 'proxy__ip')
    readonly_fields = ('assigned_at',)
    raw_id_fields = ('user', 'proxy')
    
    def proxy_status(self, obj):
        """Muestra el estado del proxy asignado."""
        return obj.proxy.status
    proxy_status.short_description = 'Estado Proxy'
    proxy_status.admin_order_field = 'proxy__status'
