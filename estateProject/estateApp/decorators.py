"""
Advanced Permission Decorators for Tenant Admin Authentication
Provides role-based and scope-based access control
"""
from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework.response import Response
from rest_framework import status


def require_system_admin(view_func):
    """
    Decorator to require system admin access for Django views.
    Redirects unauthorized users to login or access denied page.
    
    Usage:
        @require_system_admin
        def tenant_admin_view(request):
            pass
    """
    @wraps(view_func)
    @login_required(login_url='tenant-admin-login')
    def wrapped_view(request, *args, **kwargs):
        # Check if user is system admin
        is_system_admin = getattr(request.user, 'is_system_admin', False)
        admin_level = getattr(request.user, 'admin_level', 'none')
        
        if not is_system_admin or admin_level != 'system':
            # Log unauthorized access attempt
            from estateApp.audit_logging import AuditLogger
            AuditLogger.log_unauthorized_access(
                user=request.user,
                action='denied_tenant_admin_access',
                resource='tenant_admin_dashboard',
                request=request,
                reason='Not a system administrator'
            )
            
            # Return error response
            if request.path.startswith('/api/'):
                return Response(
                    {'error': 'Access Denied: System admin access required'},
                    status=status.HTTP_403_FORBIDDEN
                )
            else:
                return JsonResponse(
                    {
                        'error': 'Access Denied: System admin access required',
                        'status': 'unauthorized'
                    },
                    status=403
                )
        
        # Log successful access
        from estateApp.audit_logging import AuditLogger
        AuditLogger.log_admin_access(
            user=request.user,
            action='tenant_admin_access',
            resource='tenant_admin_dashboard',
            request=request
        )
        
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
        @login_required(login_url='login')
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
                from estateApp.audit_logging import AuditLogger
                AuditLogger.log_unauthorized_access(
                    user=request.user,
                    action=f'denied_{required_level}_admin_access',
                    resource=f'{required_level}_admin_view',
                    request=request,
                    reason=f'Required level: {required_level}, User level: {user_level}'
                )
                
                error_msg = f'Access Denied: {required_level.title()} admin access required'
                
                if request.path.startswith('/api/'):
                    return Response(
                        {'error': error_msg},
                        status=status.HTTP_403_FORBIDDEN
                    )
                else:
                    return JsonResponse({'error': error_msg}, status=403)
            
            # Log successful access
            from estateApp.audit_logging import AuditLogger
            AuditLogger.log_admin_action(
                user=request.user,
                action=f'accessed_{required_level}_admin_view',
                resource=f'{required_level}_admin_view',
                request=request
            )
            
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
    @login_required(login_url='login')
    def wrapped_view(request, *args, **kwargs):
        admin_level = getattr(request.user, 'admin_level', 'none')
        
        if admin_level not in ['system', 'company']:
            # Log unauthorized access
            from estateApp.audit_logging import AuditLogger
            AuditLogger.log_unauthorized_access(
                user=request.user,
                action='denied_company_admin_access',
                resource='company_admin_view',
                request=request,
                reason='Not an admin'
            )
            
            if request.path.startswith('/api/'):
                return Response(
                    {'error': 'Access Denied: Admin access required'},
                    status=status.HTTP_403_FORBIDDEN
                )
            else:
                return JsonResponse({'error': 'Access Denied: Admin access required'}, status=403)
        
        # Log successful access
        from estateApp.audit_logging import AuditLogger
        AuditLogger.log_admin_action(
            user=request.user,
            action='accessed_company_admin_view',
            resource='company_admin_view',
            request=request
        )
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def verify_jwt_scope(required_scope='tenant_admin'):
    """
    Decorator to verify JWT scope claim.
    Used for API endpoints that require specific JWT scope.
    
    Usage:
        @verify_jwt_scope('tenant_admin')
        def tenant_admin_api_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Get token from request
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            
            if not auth_header.startswith('Bearer '):
                return Response(
                    {'error': 'Missing or invalid authorization header'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            token = auth_header.split(' ')[1]
            
            try:
                # Decode JWT
                from estateApp.utils import decode_jwt_token
                decoded = decode_jwt_token(token)
                
                # Check scope
                if decoded.get('scope') != required_scope:
                    return Response(
                        {'error': f'Invalid scope: required {required_scope}'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Attach decoded token to request for use in view
                request.token_claims = decoded
                
            except Exception as e:
                return Response(
                    {'error': f'Invalid token: {str(e)}'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


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
        user_company_id = getattr(request.user.company_profile, 'id', None)
        
        if not user_company_id or str(user_company_id) != str(company_id):
            from estateApp.audit_logging import AuditLogger
            AuditLogger.log_unauthorized_access(
                user=request.user,
                action='denied_company_access',
                resource=f'company_{company_id}',
                request=request,
                reason='Company ownership mismatch'
            )
            
            return Response(
                {'error': 'You can only access your own company'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def audit_action(action_type='unknown', resource='unknown'):
    """
    Decorator to automatically log admin actions to audit trail.
    
    Usage:
        @audit_action('create', 'user')
        def create_user_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            from estateApp.audit_logging import AuditLogger
            
            try:
                # Execute the view
                response = view_func(request, *args, **kwargs)
                
                # Log successful action
                status_code = getattr(response, 'status_code', 200)
                
                if 200 <= status_code < 300:
                    AuditLogger.log_admin_action(
                        user=request.user,
                        action=action_type,
                        resource=resource,
                        request=request,
                        status='success',
                        details={'status_code': status_code}
                    )
                else:
                    AuditLogger.log_admin_action(
                        user=request.user,
                        action=action_type,
                        resource=resource,
                        request=request,
                        status='failure',
                        details={'status_code': status_code}
                    )
                
                return response
            
            except Exception as e:
                # Log error
                AuditLogger.log_admin_action(
                    user=request.user,
                    action=action_type,
                    resource=resource,
                    request=request,
                    status='error',
                    details={'error': str(e)}
                )
                raise
        
        return wrapped_view
    return decorator
