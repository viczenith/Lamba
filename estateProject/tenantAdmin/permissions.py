"""
Tenant Admin Permission Classes
Secure access control for system-wide management
"""
from rest_framework.permissions import BasePermission


class IsSystemAdmin(BasePermission):
    """
    Allows access only to system administrators.
    Used for Tenant Admin endpoints.
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
    System admins have full access, others can only read
    """
    message = "Only system administrators can modify this resource"
    
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return request.user and request.user.is_authenticated
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        is_system_admin = getattr(request.user, 'is_system_admin', False)
        admin_level = getattr(request.user, 'admin_level', None)
        
        return is_system_admin and admin_level == 'system'


class IsSuperAdminOnly(BasePermission):
    """
    Restricted to Django superusers only (highest privilege)
    """
    message = "Access Denied: Superuser access required"
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser
