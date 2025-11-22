"""
Custom authentication backend to handle non-unique email addresses
across multiple companies in multi-tenant system.
"""
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import CustomUser


class MultiTenantAuthBackend(ModelBackend):
    """
    Custom authentication backend that handles login for users with same email
    across different companies.
    
    Authentication logic:
    1. If only one user found with email -> authenticate normally
    2. If multiple users found -> need additional context (company) to disambiguate
    """
    
    def authenticate(self, request, username=None, password=None, company=None, **kwargs):
        """
        Authenticate user by email and password.
        
        Args:
            username: Email address (USERNAME_FIELD)
            password: User password
            company: Company context for disambiguation (optional)
        """
        if username is None or password is None:
            return None
        
        try:
            # Find all users with this email
            users = CustomUser.objects.filter(email=username, is_active=True)
            
            if not users.exists():
                return None
            
            # If only one user, authenticate normally
            if users.count() == 1:
                user = users.first()
                if user.check_password(password):
                    return user
                return None
            
            # Multiple users with same email - need company context
            if company:
                # Try to find user in specific company
                user = users.filter(company_profile=company).first()
                if user and user.check_password(password):
                    return user
            
            # If no company provided or not found, try to authenticate first matching user
            # This handles cases where user is logging in from non-company-specific login
            for user in users:
                if user.check_password(password):
                    # Return the first user that matches
                    # In practice, you might want to show a company selection screen
                    return user
            
            return None
            
        except CustomUser.DoesNotExist:
            return None
    
    def get_user(self, user_id):
        """
        Get user by ID for session management.
        """
        try:
            return CustomUser.objects.get(pk=user_id, is_active=True)
        except CustomUser.DoesNotExist:
            return None
