from django.contrib import admin
from .models import ProxyIP, UserProxyAssignment


@admin.register(ProxyIP)
class ProxyIPAdmin(admin.ModelAdmin):
    list_display = ('id', 'ip', 'port', 'max_accounts', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('ip',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UserProxyAssignment)
class UserProxyAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'proxy', 'assigned_at', 'last_used_at')
    list_filter = ('proxy',)
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('assigned_at',)
    raw_id_fields = ('user', 'proxy')
