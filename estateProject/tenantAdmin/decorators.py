"""
Tenant Admin Decorators
View decorators for access control and auditing
"""
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


def require_system_admin(view_func):
    """
    Decorator to require system admin access for views.
    Redirects to login if not authenticated or access denied page if not system admin.
    """
    @wraps(view_func)
    @login_required(login_url='tenant_admin:login')
    def wrapped_view(request, *args, **kwargs):
        # Check if user is system admin
        is_system_admin = getattr(request.user, 'is_system_admin', False)
        admin_level = getattr(request.user, 'admin_level', 'none')
        
        if not is_system_admin or admin_level != 'system':
            # Return appropriate response based on request type
            if request.path.startswith('/api/'):
                return JsonResponse(
                    {
                        'error': 'Access Denied: System admin access required',
                        'status': 'unauthorized'
                    },
                    status=403
                )
            else:
                return redirect('tenant_admin:access-denied')
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def require_superuser(view_func):
    """
    Decorator to require Django superuser access
    """
    @wraps(view_func)
    @login_required(login_url='tenant_admin:login')
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            if request.path.startswith('/api/'):
                return JsonResponse(
                    {
                        'error': 'Access Denied: Superuser access required',
                        'status': 'unauthorized'
                    },
                    status=403
                )
            else:
                return redirect('tenant_admin:access-denied')
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def audit_action(action_type='unknown', resource='unknown'):
    """
    Decorator to automatically log admin actions
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Execute the view
            response = view_func(request, *args, **kwargs)
            
            # Log the action (implement audit logging here)
            try:
                from tenantAdmin.models import AuditLog
                AuditLog.objects.create(
                    user=request.user,
                    action_type=action_type,
                    resource=resource,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_method=request.method,
                    request_path=request.path
                )
            except Exception as e:
                # Don't fail the request if audit logging fails
                print(f"Audit logging failed: {e}")
            
            return response
        
        return wrapped_view
    return decorator
