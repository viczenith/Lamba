"""
Permission classes for SuperAdmin app - Platform-level access control
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.exceptions import PermissionDenied


class IsSystemAdmin(BasePermission):
    """
    Allows access only to system administrators.
    Used for platform-level Tenant Admin endpoints.
    
    System admins must have:
    - is_system_admin = True
    - admin_level = 'system'
    - company_profile = None (platform-level, not company-specific)
    """
    message = "Access Denied: System admin access required"
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        is_system_admin = getattr(request.user, 'is_system_admin', False)
        admin_level = getattr(request.user, 'admin_level', None)
        
        return is_system_admin and admin_level == 'system'


class IsSystemAdminOrReadOnly(BasePermission):
    """
    System admins get full access, others get read-only.
    """
    message = "Only system administrators can perform this action"
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read permissions for any authenticated user
        if request.method in SAFE_METHODS:
            return True
        
        # Write permissions only for system admins
        is_system_admin = getattr(request.user, 'is_system_admin', False)
        admin_level = getattr(request.user, 'admin_level', None)
        
        return is_system_admin and admin_level == 'system'


class IsCompanyAdmin(BasePermission):
    """
    Allows access to company admins (system or company level).
    Used for company-specific admin features.
    """
    message = "Access Denied: Admin access required"
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        admin_level = getattr(request.user, 'admin_level', 'none')
        
        # Allow system admins and company admins
        return admin_level in ['system', 'company']


class IsSuperAdminOnly(BasePermission):
    """
    Restricts access to Django superusers only.
    Most restrictive permission - for critical operations.
    """
    message = "Access Denied: Superuser access required"
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.is_superuser


class PlatformAccessPermission(BasePermission):
    """
    Check if user has platform-level access (not restricted to a single company).
    System admins have platform access, regular users don't.
    """
    message = "Platform-level access required"
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        is_system_admin = getattr(request.user, 'is_system_admin', False)
        admin_level = getattr(request.user, 'admin_level', 'none')
        
        # System admins have platform access
        if is_system_admin and admin_level == 'system':
            return True
        
        # Check if view allows company admins
        allow_company_admin = getattr(view, 'allow_company_admin_access', False)
        if allow_company_admin and admin_level == 'company':
            return True
        
        return False
