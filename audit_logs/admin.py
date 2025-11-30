from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user_id', 'action_type', 'resource_type', 'resource_id', 'ip_address')
    list_filter = ('action_type', 'resource_type', 'timestamp')
    search_fields = ('user_id', 'resource_id', 'ip_address')
    readonly_fields = ('timestamp', 'user_id', 'action_type', 'resource_type', 'resource_id', 'metadata', 'ip_address', 'user_agent')
    ordering = ('-timestamp',)
    
    def has_add_permission(self, request):
        # Prevent manual creation of audit logs
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of audit logs
        return False
