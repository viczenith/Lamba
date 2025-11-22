"""
Advanced Permission Decorators for SuperAdmin - Platform-level access control
Provides role-based and scope-based access control for system administrators
"""
from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from rest_framework.response import Response
from rest_framework import status


def require_system_admin(view_func):
    """
    Decorator to require system admin access for Django views.
    Redirects unauthorized users to the beautiful login page.
    
    Usage:
        @require_system_admin
        def platform_admin_view(request):
            pass
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            from django.urls import reverse
            login_url = reverse('superadmin:login')
            next_url = request.get_full_path()
            return redirect(f'{login_url}?next={next_url}')
        # Check if user is system admin
        is_system_admin = getattr(request.user, 'is_system_admin', False)
        admin_level = getattr(request.user, 'admin_level', 'none')
        
        if not is_system_admin or admin_level != 'system':
            # Log unauthorized access attempt
            try:
                from superAdmin.models import SystemAuditLog
                SystemAuditLog.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    action='DENIED_ACCESS',
                    resource='platform_admin_dashboard',
                    status='FAILED',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={'reason': 'Not a system administrator'}
                )
            except Exception:
                pass  # Don't fail the request if logging fails
            
            # Return error response
            if request.path.startswith('/api/'):
                return Response(
                    {'error': 'Access Denied: System admin access required'},
                    status=status.HTTP_403_FORBIDDEN
                )
            else:
                return redirect('/super-admin/access-denied/')
        
        # Log successful access
        try:
            from superAdmin.models import SystemAuditLog
            SystemAuditLog.objects.create(
                user=request.user,
                action='ACCESS_GRANTED',
                resource='platform_admin_dashboard',
                status='SUCCESS',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        except Exception:
            pass
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def require_admin_level(required_level='system'):
    """
    Decorator to check specific admin level.
    
    Args:
        required_level: 'system' (only system admins) or 'company' (system or company admins)
    
    Usage:
        @require_admin_level('system')
        def system_only_view(request):
            pass
        
        @require_admin_level('company')
        def company_admin_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='/login/')
        def wrapped_view(request, *args, **kwargs):
            user_level = getattr(request.user, 'admin_level', 'none')
            
            # Check if user has required level
            if required_level == 'system':
                has_access = user_level == 'system'
            elif required_level == 'company':
                has_access = user_level in ['system', 'company']
            else:
                has_access = False
            
            if not has_access:
                # Log unauthorized access
                try:
                    from superAdmin.models import SystemAuditLog
                    SystemAuditLog.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        action='DENIED_ACCESS',
                        resource=f'{required_level}_admin_view',
                        status='FAILED',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        details={
                            'required_level': required_level,
                            'user_level': user_level
                        }
                    )
                except Exception:
                    pass
                
                error_msg = f'Access Denied: {required_level.title()} admin access required'
                
                if request.path.startswith('/api/'):
                    return Response(
                        {'error': error_msg},
                        status=status.HTTP_403_FORBIDDEN
                    )
                else:
                    return JsonResponse({'error': error_msg}, status=403)
            
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


def require_company_admin(view_func):
    """
    Decorator to require company admin access.
    Allows both system admins and company admins (for their own company).
    
    Usage:
        @require_company_admin
        def company_admin_view(request):
            pass
    """
    @wraps(view_func)
    @login_required(login_url='/login/')
    def wrapped_view(request, *args, **kwargs):
        admin_level = getattr(request.user, 'admin_level', 'none')
        
        if admin_level not in ['system', 'company']:
            if request.path.startswith('/api/'):
                return Response(
                    {'error': 'Access Denied: Admin access required'},
                    status=status.HTTP_403_FORBIDDEN
                )
            else:
                return JsonResponse({'error': 'Access Denied: Admin access required'}, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def check_company_ownership(view_func):
    """
    Decorator to verify user owns the company being accessed.
    Company ID should be in request.POST, request.GET, or kwargs.
    
    Usage:
        @check_company_ownership
        def company_view(request, company_id):
            pass
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Get company_id from various sources
        company_id = (
            kwargs.get('company_id') or
            request.POST.get('company_id') or
            request.GET.get('company_id')
        )
        
        if not company_id:
            return Response(
                {'error': 'Company ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # System admins can access any company
        if getattr(request.user, 'is_system_admin', False):
            return view_func(request, *args, **kwargs)
        
        # Company admins can only access their own company
        user_company_id = getattr(request.user.company_profile, 'id', None) if hasattr(request.user, 'company_profile') else None
        
        if not user_company_id or str(user_company_id) != str(company_id):
            return Response(
                {'error': 'You can only access your own company'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def audit_action(action_type='UNKNOWN', resource='unknown'):
    """
    Decorator to automatically log admin actions to audit trail.
    
    Usage:
        @audit_action('CREATE', 'user')
        def create_user_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            try:
                # Execute the view
                response = view_func(request, *args, **kwargs)
                
                # Log successful action
                status_code = getattr(response, 'status_code', 200)
                
                try:
                    from superAdmin.models import SystemAuditLog
                    SystemAuditLog.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        action=action_type.upper(),
                        resource=resource,
                        status='SUCCESS' if 200 <= status_code < 300 else 'FAILED',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        details={'status_code': status_code}
                    )
                except Exception:
                    pass
                
                return response
            
            except Exception as e:
                # Log error
                try:
                    from superAdmin.models import SystemAuditLog
                    SystemAuditLog.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        action=action_type.upper(),
                        resource=resource,
                        status='FAILED',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        details={'error': str(e)}
                    )
                except Exception:
                    pass
                raise
        
        return wrapped_view
    return decorator


def require_superuser(view_func):
    """
    Decorator to require Django superuser status (most restrictive).
    
    Usage:
        @require_superuser
        def critical_operation_view(request):
            pass
    """
    @wraps(view_func)
    @login_required(login_url='/super-admin/login/')
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            if request.path.startswith('/api/'):
                return Response(
                    {'error': 'Access Denied: Superuser access required'},
                    status=status.HTTP_403_FORBIDDEN
                )
            else:
                return redirect('/super-admin/access-denied/')
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view
