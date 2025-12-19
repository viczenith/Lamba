"""
Client Permission Classes
==========================
DRF permission classes for client API endpoints.

This module provides secure permission checks for:
- Client user role verification (IsClientUser)
- Object-level recipient validation (IsRecipient)

SECURITY IMPLEMENTATIONS:
1. Role-based access control
2. Object-level permission checks
3. Authentication verification
4. Audit logging for denied access

Author: System
Version: 2.0
Last Updated: December 2024
"""

from rest_framework.permissions import BasePermission
from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)


class IsRecipient(BasePermission):
    """
    Object-level permission to allow only the recipient to access a UserNotification instance.
    
    SECURITY:
    - Validates user owns the notification
    - Prevents cross-user data access
    - Logs unauthorized access attempts
    """
    message = "You do not have permission to access this notification."
    
    def has_object_permission(self, request, view, obj):
        # obj is a UserNotification instance
        user = request.user
        
        if not user or not user.is_authenticated:
            logger.warning(f"SECURITY: Unauthenticated access attempt to notification")
            return False
        
        # Check if user is the recipient
        is_recipient = obj.user_id == user.id
        
        if not is_recipient:
            logger.warning(
                f"SECURITY: User {user.id} attempted to access notification {obj.id} "
                f"belonging to user {obj.user_id}"
            )
        
        return is_recipient


class IsClientUser(permissions.BasePermission):
    """
    Permission class to verify user has 'client' role.
    
    SECURITY:
    - Validates authentication
    - Checks user role is 'client'
    - Logs unauthorized access attempts
    - Prevents non-client users from accessing client-only endpoints
    """
    message = "Access restricted to client users only."
    
    def has_permission(self, request, view):
        user = request.user
        
        # Check authentication
        if not user or not user.is_authenticated:
            logger.warning(f"SECURITY: Unauthenticated access to client endpoint: {request.path}")
            return False
        
        # Check role
        user_role = getattr(user, 'role', None)
        is_client = user_role == 'client'
        
        if not is_client:
            logger.warning(
                f"SECURITY: Non-client user {user.id} (role={user_role}) "
                f"attempted to access client endpoint: {request.path}"
            )
        
        return is_client


class IsCompanyMember(permissions.BasePermission):
    """
    Permission class to verify user belongs to a company.
    
    SECURITY:
    - Validates user has company affiliation
    - Works with multi-tenant architecture
    """
    message = "Access restricted to company members only."
    
    def has_permission(self, request, view):
        user = request.user
        
        if not user or not user.is_authenticated:
            return False
        
        # Check direct company affiliation
        if hasattr(user, 'company_profile') and user.company_profile:
            return True
        
        # Check CompanyClientProfile
        try:
            from estateApp.models import CompanyClientProfile
            return CompanyClientProfile.objects.filter(user=user).exists()
        except Exception:
            return False


class IsAuthenticatedClient(permissions.BasePermission):
    """
    Combined permission: authenticated AND client role.
    
    SECURITY:
    - Single permission class combining auth + role check
    - More efficient than stacking multiple permissions
    """
    message = "Authentication required. Access restricted to client users."
    
    def has_permission(self, request, view):
        user = request.user
        
        if not user or not user.is_authenticated:
            return False
        
        return getattr(user, 'role', None) == 'client'
    
    
