"""
Tenant Admin - Django Admin Registration
"""
from django.contrib import admin
from .models import AuditLog, SystemConfiguration, SystemAlert, SystemMetric


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Audit Log Admin
    """
    list_display = ['user', 'action_type', 'resource', 'company', 'timestamp']
    list_filter = ['action_type', 'timestamp', 'company']
    search_fields = ['user__email', 'user__full_name', 'resource', 'description']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False  # Audit logs are created automatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Audit logs are immutable


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    """
    System Configuration Admin
    """
    list_display = ['key', 'value_type', 'is_sensitive', 'updated_at', 'updated_by']
    list_filter = ['value_type', 'is_sensitive']
    search_fields = ['key', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SystemAlert)
class SystemAlertAdmin(admin.ModelAdmin):
    """
    System Alert Admin
    """
    list_display = ['title', 'severity', 'alert_type', 'is_active', 'is_resolved', 'created_at']
    list_filter = ['severity', 'alert_type', 'is_active', 'is_resolved']
    search_fields = ['title', 'message']
    readonly_fields = ['created_at', 'updated_at', 'resolved_at']
    date_hierarchy = 'created_at'
    
    actions = ['mark_as_resolved']
    
    def mark_as_resolved(self, request, queryset):
        for alert in queryset:
            alert.resolve(request.user)
        self.message_user(request, f'{queryset.count()} alerts marked as resolved')
    mark_as_resolved.short_description = 'Mark selected alerts as resolved'


@admin.register(SystemMetric)
class SystemMetricAdmin(admin.ModelAdmin):
    """
    System Metric Admin
    """
    list_display = ['metric_name', 'metric_value', 'metric_unit', 'timestamp']
    list_filter = ['metric_name', 'timestamp']
    search_fields = ['metric_name']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    def has_change_permission(self, request, obj=None):
        return False  # Metrics are immutable
