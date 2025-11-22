"""
Tenant Admin Views - Dashboard and Authentication
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib import messages

from .decorators import require_system_admin


class TenantAdminLoginView(View):
    """
    System Admin Login
    """
    template_name = 'tenantAdmin/login.html'
    
    def get(self, request):
        if request.user.is_authenticated and request.user.is_system_admin:
            return redirect('tenant_admin:dashboard')
        return render(request, self.template_name)
    
    def post(self, request):
        # Login logic handled by DRF endpoint
        pass


class TenantAdminLogoutView(View):
    """
    System Admin Logout
    """
    def post(self, request):
        logout(request)
        messages.success(request, "Successfully logged out")
        return redirect('tenant_admin:login')


@method_decorator(require_system_admin, name='dispatch')
class TenantAdminDashboardView(View):
    """
    System-wide Management Dashboard
    SECURITY: Requires is_system_admin=True and admin_level='system'
    """
    template_name = 'tenantAdmin/dashboard.html'
    
    def get(self, request):
        context = {
            'admin': request.user,
            'page_title': 'Tenant Admin Dashboard',
        }
        return render(request, self.template_name, context)


class AccessDeniedView(View):
    """
    Access Denied Page
    """
    template_name = 'tenantAdmin/access_denied.html'
    
    def get(self, request):
        return render(request, self.template_name)
