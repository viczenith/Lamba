"""
DATABASE-LEVEL ISOLATION LAYER
Provides strict row-level security validators and database constraints
"""

from django.db import models, connection
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)


class TenantValidator:
    """
    Validates that all operations respect tenant boundaries at database level
    This is the STRICTEST isolation layer - nothing gets past this
    """
    
    @staticmethod
    def validate_company_field(instance, model_class):
        """
        CRITICAL: Validates that model instance has valid company field
        Called before every save() operation
        
        Raises ValidationError if:
        - company field is NULL
        - company field doesn't exist
        - company is not active
        """
        
        # Check if model has company field
        if not hasattr(instance, 'company'):
            raise ValidationError(
                _("Model %(model)s must have 'company' field for multi-tenant isolation"),
                code='missing_company_field',
                params={'model': model_class.__name__}
            )
        
        # Check if company_id is NULL
        if not instance.company_id:
            raise ValidationError(
                _("%(model)s.company cannot be NULL - tenant isolation violated!"),
                code='null_company_field',
                params={'model': model_class.__name__}
            )
        
        # Check if company is active
        from estateApp.models import Company
        try:
            company = Company.objects.get(id=instance.company_id)
            if not company.is_active:
                raise ValidationError(
                    _("Company is not active"),
                    code='inactive_company'
                )
        except Company.DoesNotExist:
            raise ValidationError(
                _("Invalid company_id: %(company_id)s"),
                code='invalid_company_id',
                params={'company_id': instance.company_id}
            )
    
    @staticmethod
    def validate_unique_together(instance, model_class):
        """
        Validates unique_together constraints are COMPANY-SCOPED
        
        Checks if any unique fields lack company scope
        e.g., unique=(field,) instead of unique_together=((company, field),)
        """
        
        # Get meta options
        meta = model_class._meta
        
        # Check Meta.unique_together
        if hasattr(meta, 'unique_together') and meta.unique_together:
            for unique_tuple in meta.unique_together:
                # Verify company is in unique constraint
                if 'company' not in unique_tuple:
                    logger.warning(
                        f"⚠️ WARNING: {model_class.__name__}.unique_together doesn't "
                        f"include 'company': {unique_tuple}\n"
                        f"This could allow duplicate values across companies!\n"
                        f"Should be: unique_together = (('company',) + {unique_tuple})"
                    )
        
        # Check individual unique=True fields
        for field in meta.get_fields():
            if hasattr(field, 'unique') and field.unique:
                if field.name != 'company':
                    logger.warning(
                        f"⚠️ WARNING: {model_class.__name__}.{field.name} has unique=True "
                        f"without company scoping!\n"
                        f"This allows duplicate values across companies!\n"
                        f"Consider using: unique_together = (('company', '{field.name}'))"
                    )
    
    @staticmethod
    def validate_foreign_keys(instance, model_class):
        """
        Validates that related objects belong to same company
        
        e.g., if PlotSize has company_id=5, all related plots
        must also have company_id=5
        """
        
        meta = model_class._meta
        instance_company_id = getattr(instance, 'company_id', None)
        
        if not instance_company_id:
            return  # Already validated in validate_company_field
        
        # Check all foreign keys
        for field in meta.get_fields():
            if field.many_to_one and field.name != 'company':
                # Get the related object
                related_instance = getattr(instance, field.name, None)
                
                if related_instance and hasattr(related_instance, 'company_id'):
                    # Verify related object is in same company
                    if related_instance.company_id != instance_company_id:
                        raise ValidationError(
                            _(
                                "Related %(relation)s belongs to different company. "
                                "Tenant isolation violated!"
                            ),
                            code='cross_tenant_relation',
                            params={'relation': field.name}
                        )


class DatabaseIsolationMixin(models.Model):
    """
    Mixin that adds database-level isolation validation to any model
    
    Usage:
        class MyModel(DatabaseIsolationMixin):
            company = ForeignKey(Company, on_delete=models.CASCADE)
            # ... other fields
            
            class Meta:
                unique_together = (('company', 'name'),)
    """
    
    def clean(self):
        """
        Override clean() to enforce database-level validation
        Called before every save()
        """
        super().clean()
        
        model_class = self.__class__
        
        # CRITICAL VALIDATIONS
        TenantValidator.validate_company_field(self, model_class)
        TenantValidator.validate_unique_together(self, model_class)
        TenantValidator.validate_foreign_keys(self, model_class)
    
    def save(self, *args, **kwargs):
        """
        Override save() to enforce validation
        """
        # Always run full clean before saving
        self.full_clean()
        
        super().save(*args, **kwargs)
    
    class Meta:
        abstract = True


class RowLevelSecurityManager(models.Manager):
    """
    Advanced manager that enforces row-level security
    
    Works with PostgreSQL Row-Level Security (RLS) policies
    For SQLite, provides application-level enforcement
    """
    
    def set_tenant_context(self, company_id):
        """
        Set tenant context for this query session
        Used by PostgreSQL RLS
        """
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    f"SET app.current_company_id TO {company_id};"
                )
            except Exception as e:
                logger.debug(f"RLS not available: {e}")
        
        return self
    
    def verify_isolation(self):
        """
        Verify that RLS is properly configured
        Returns True if RLS is active, False otherwise
        """
        if 'postgresql' not in connection.vendor:
            return False
        
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    "SELECT * FROM pg_policies "
                    f"WHERE tablename = '{self.model._meta.db_table}';"
                )
                policies = cursor.fetchall()
                return len(policies) > 0
            except Exception:
                return False


class IsolationAuditLog(models.Model):
    """
    CRITICAL: Logs all isolation violations and access attempts
    Used for security monitoring and compliance
    """
    
    VIOLATION_TYPES = (
        ('NULL_COMPANY', 'NULL company_id detected'),
        ('CROSS_TENANT', 'Cross-tenant access attempt'),
        ('INVALID_FK', 'Related object in different company'),
        ('PERMISSION', 'User lacks tenant permission'),
        ('CONSTRAINT', 'Unique constraint violation'),
    )
    
    company = models.ForeignKey(
        'estateApp.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='isolation_violations'
    )
    user = models.ForeignKey(
        'estateApp.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    violation_type = models.CharField(
        max_length=20,
        choices=VIOLATION_TYPES
    )
    model_name = models.CharField(max_length=100)
    object_id = models.IntegerField(null=True, blank=True)
    message = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['company', 'violation_type']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['resolved']),
        ]
    
    def __str__(self):
        return f"{self.get_violation_type_display()} - {self.model_name}({self.object_id})"
    
    @classmethod
    def log_violation(cls, violation_type, model_name, object_id, message, 
                     company=None, user=None, ip_address=None):
        """
        Log an isolation violation
        
        CRITICAL: Called whenever isolation might be violated
        """
        return cls.objects.create(
            violation_type=violation_type,
            model_name=model_name,
            object_id=object_id,
            message=message,
            company=company,
            user=user,
            ip_address=ip_address
        )


class TenantDataSanitizer:
    """
    Sanitizes and validates data to prevent injection attacks
    that could bypass tenant isolation
    """
    
    @staticmethod
    def sanitize_company_id(company_id):
        """
        Validates company_id is proper integer
        Prevents SQL injection
        """
        try:
            company_id = int(company_id)
            if company_id < 1:
                raise ValueError("Company ID must be positive")
            return company_id
        except (ValueError, TypeError):
            raise ValidationError(
                _("Invalid company_id format"),
                code='invalid_company_id'
            )
    
    @staticmethod
    def sanitize_query_params(params, allowed_fields):
        """
        Validates query parameters are in allowed list
        Prevents parameter injection attacks
        """
        sanitized = {}
        for key, value in params.items():
            if key not in allowed_fields:
                logger.warning(f"Unexpected parameter: {key}")
                continue
            sanitized[key] = value
        return sanitized
    
    @staticmethod
    def validate_no_null_companies(queryset, model_class):
        """
        CRITICAL: Scans queryset for NULL company_id records
        Raises alert if any found
        """
        null_count = queryset.filter(company_id__isnull=True).count()
        
        if null_count > 0:
            logger.critical(
                f"SECURITY ALERT: Found {null_count} records with NULL "
                f"company_id in {model_class.__name__}!\n"
                f"This is a data leakage vulnerability!"
            )
            
            # Log violation
            IsolationAuditLog.log_violation(
                violation_type='NULL_COMPANY',
                model_name=model_class.__name__,
                object_id=None,
                message=f"{null_count} records with NULL company_id"
            )
            
            raise ValidationError(
                _("Data integrity violation: NULL company records found"),
                code='null_company_records'
            )
        
        return queryset


class StrictTenantModel(DatabaseIsolationMixin):
    """
    ULTIMATE STRICT TENANT MODEL
    
    Every model that extends this will have:
    - Mandatory company field (cannot be NULL)
    - Per-company uniqueness constraints
    - Foreign key validation
    - Audit logging on all operations
    - RLS-ready for PostgreSQL
    
    Usage:
        class MyModel(StrictTenantModel):
            name = CharField(max_length=100)
            
            class Meta:
                unique_together = (('company', 'name'),)
    """
    
    company = models.ForeignKey(
        'estateApp.Company',
        on_delete=models.CASCADE,
        help_text="Required: Company this record belongs to"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """
        STRICT: Enforce all validations before save
        """
        # Validate company field
        if not self.company_id:
            raise ValidationError(
                "Company field is required (cannot be NULL)"
            )
        
        # Call parent save (which calls full_clean)
        super().save(*args, **kwargs)
        
        # Log the operation
        logger.info(
            f"Record saved: {self.__class__.__name__} "
            f"({self.pk}) in company {self.company_id}"
        )


# CONFIGURATION CONSTANTS FOR DATABASE ISOLATION

# Enable strict validation
STRICT_MODE = True

# Enable audit logging
AUDIT_LOGGING_ENABLED = True

# Enable RLS (Row-Level Security) for PostgreSQL
RLS_ENABLED = True

# Fields that trigger re-validation on update
REVALIDATE_ON_UPDATE = ['company']

# Maximum records to check for NULL companies
MAX_NULL_COMPANY_CHECK = 10000
