"""
Tenant Admin Models
Database models for system-wide management
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class AuditLog(models.Model):
    """
    System-wide audit logging for compliance and security
    """
    ACTION_TYPES = [
        ('create', 'Create'),
        ('read', 'Read'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('access_denied', 'Access Denied'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tenant_audit_logs'
    )
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    resource = models.CharField(max_length=255, help_text="What was accessed/modified")
    resource_id = models.CharField(max_length=100, blank=True, null=True)
    company = models.ForeignKey(
        'estateApp.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tenant_audit_logs'
    )
    
    # Request details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    
    # Additional context
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp', 'action_type']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['company', '-timestamp']),
        ]
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
    
    def __str__(self):
        return f"{self.user} - {self.action_type} - {self.resource} at {self.timestamp}"


class SystemConfiguration(models.Model):
    """
    System-wide configuration settings
    """
    key = models.CharField(max_length=255, unique=True, db_index=True)
    value = models.TextField()
    value_type = models.CharField(
        max_length=20,
        choices=[
            ('string', 'String'),
            ('integer', 'Integer'),
            ('float', 'Float'),
            ('boolean', 'Boolean'),
            ('json', 'JSON'),
        ],
        default='string'
    )
    description = models.TextField(blank=True)
    is_sensitive = models.BooleanField(default=False, help_text="Sensitive data (passwords, keys)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='config_updates'
    )
    
    class Meta:
        ordering = ['key']
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configurations'
    
    def __str__(self):
        return f"{self.key} = {self.value if not self.is_sensitive else '***'}"
    
    def get_value(self):
        """Return the value in its appropriate type"""
        if self.value_type == 'integer':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'boolean':
            return self.value.lower() in ['true', '1', 'yes']
        elif self.value_type == 'json':
            import json
            return json.loads(self.value)
        return self.value


class SystemAlert(models.Model):
    """
    System-wide alerts and notifications for admins
    """
    SEVERITY_LEVELS = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='info')
    
    # Alert metadata
    alert_type = models.CharField(max_length=50, blank=True)
    source = models.CharField(max_length=100, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tenant_resolved_alerts'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
        ]
        verbose_name = 'System Alert'
        verbose_name_plural = 'System Alerts'
    
    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"
    
    def resolve(self, user=None):
        """Mark alert as resolved"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.save()


class SystemMetric(models.Model):
    """
    Time-series metrics for system monitoring
    """
    metric_name = models.CharField(max_length=100, db_index=True)
    metric_value = models.FloatField()
    metric_unit = models.CharField(max_length=50, blank=True)
    
    # Metadata
    tags = models.JSONField(default=dict, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['metric_name', '-timestamp']),
        ]
        verbose_name = 'System Metric'
        verbose_name_plural = 'System Metrics'
    
    def __str__(self):
        return f"{self.metric_name}: {self.metric_value}{self.metric_unit} at {self.timestamp}"

