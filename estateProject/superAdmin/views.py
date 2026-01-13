"""
Super Admin Views - Dashboard and Management
Platform-level administration interface for multi-tenant SaaS
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.generic import TemplateView, ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from decimal import Decimal

from .models import (
    PlatformConfiguration, SuperAdminUser, CompanySubscription,
    PlatformInvoice, PlatformAnalytics, SystemAuditLog, CompanyOnboarding,
    FeatureFlag, SystemNotification, SubscriptionPlan
)
from estateApp.models import Company, CustomUser
from .decorators import require_system_admin, require_superuser
from .permissions import IsSystemAdmin


def is_system_admin(user):
    """
    Check if user is a system administrator (platform-level access).
    Replaces old is_super_admin check.
    """
    return (
        user.is_authenticated and 
        getattr(user, 'is_system_admin', False) and 
        getattr(user, 'admin_level', 'none') == 'system'
    )


class SystemAdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin to restrict access to system admins only.
    Replaces SuperAdminRequiredMixin for consistency.
    """
    login_url = '/super-admin/login/'
    
    def test_func(self):
        return is_system_admin(self.request.user)
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(f'{self.login_url}?next={self.request.get_full_path()}')
        return redirect('superadmin:access_denied')


# Keep backward compatibility alias
SuperAdminRequiredMixin = SystemAdminRequiredMixin


class SuperAdminLoginView(View):
    """
    Beautiful login page for Platform Super Admins
    Enhanced with honeypot protection and security measures
    """
    template_name = 'superAdmin/login.html'
    
    def get(self, request):
        # Redirect if already logged in as system admin
        if is_system_admin(request.user):
            return redirect('superadmin:dashboard')
        
        # Generate honeypot field name (changes per request)
        import secrets
        honeypot_field = secrets.token_hex(8)
        request.session['honeypot_field'] = honeypot_field
        
        return render(request, self.template_name, {
            'page_title': 'Platform Admin Login',
            'year': timezone.now().year,
            'honeypot_field': honeypot_field
        })
    
    def post(self, request):
        # Honeypot check - if filled, it's a bot
        honeypot_field = request.session.get('honeypot_field', 'username')
        if request.POST.get(honeypot_field, ''):
            # Log bot attempt
            try:
                SystemAuditLog.objects.create(
                    user=None,
                    action='BOT_DETECTED',
                    resource='platform_admin_login',
                    status='FAILED',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={'reason': 'Honeypot field filled', 'honeypot_field': honeypot_field}
                )
            except Exception:
                pass
            
            # Return fake error to not reveal detection
            messages.error(request, 'Invalid email or password. Please try again.')
            return render(request, self.template_name, {
                'page_title': 'Platform Admin Login',
                'year': timezone.now().year,
                'honeypot_field': honeypot_field
            })
        
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me', False)
        
        if not email or not password:
            messages.error(request, 'Please provide both email and password.')
            return render(request, self.template_name, {
                'email': email,
                'page_title': 'Platform Admin Login',
                'year': timezone.now().year,
                'honeypot_field': honeypot_field
            })
        
        # Authenticate user
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            # Check if user is a system administrator
            if not getattr(user, 'is_system_admin', False) or getattr(user, 'admin_level', 'none') != 'system':
                messages.error(request, 'Access Denied: You do not have platform administrator privileges.')
                
                # Log unauthorized access attempt
                try:
                    SystemAuditLog.objects.create(
                        user=user,
                        action='LOGIN_DENIED',
                        resource='platform_admin_login',
                        status='FAILED',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        details={'reason': 'Not a system administrator', 'email': email}
                    )
                except Exception:
                    pass
                
                return render(request, self.template_name, {
                    'email': email,
                    'page_title': 'Platform Admin Login',
                    'year': timezone.now().year
                })
            
            # Login successful
            login(request, user)
            
            # Set session expiry
            if not remember_me:
                request.session.set_expiry(0)  # Session expires when browser closes
            else:
                request.session.set_expiry(1209600)  # 2 weeks
            
            # Set custom session expiry for middleware
            import time
            current_time = time.time()
            if not remember_me:
                request.session['_session_expiry'] = current_time + 300  # 5 minutes
            else:
                request.session['_session_expiry'] = current_time + 1209600  # 2 weeks
            # Set security session variables for SessionSecurityMiddleware
            request.session['_security_last_activity'] = current_time
            request.session['_security_session_created'] = current_time
            request.session.save()
            
            # Log successful login
            try:
                SystemAuditLog.objects.create(
                    user=user,
                    action='LOGIN',
                    resource='platform_admin_dashboard',
                    status='SUCCESS',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={'email': email}
                )
            except Exception:
                pass
            
            messages.success(request, f'Welcome back, {user.full_name}!')
            
            # Redirect to next URL or dashboard
            next_url = request.GET.get('next', 'superadmin:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password. Please try again.')
            
            # Log failed login attempt
            try:
                SystemAuditLog.objects.create(
                    user=None,
                    action='LOGIN_FAILED',
                    resource='platform_admin_login',
                    status='FAILED',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={'email': email, 'reason': 'Invalid credentials'}
                )
            except Exception:
                pass
            
            return render(request, self.template_name, {
                'email': email,
                'page_title': 'Platform Admin Login',
                'year': timezone.now().year
            })


class SuperAdminLogoutView(View):
    """
    Logout view for Platform Super Admins
    """
    
    def get(self, request):
        return self.post(request)
    
    def post(self, request):
        if request.user.is_authenticated:
            # Log logout
            try:
                SystemAuditLog.objects.create(
                    user=request.user,
                    action='LOGOUT',
                    resource='platform_admin_dashboard',
                    status='SUCCESS',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            except Exception:
                pass
            
            user_name = request.user.full_name
            logout(request)
            messages.success(request, f'Goodbye, {user_name}! You have been logged out.')
        
        return redirect('superadmin:login')


class SuperAdminDashboardView(LoginRequiredMixin, SuperAdminRequiredMixin, TemplateView):
    """Main super admin dashboard"""
    template_name = 'superAdmin/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get today's analytics
        today = timezone.now().date()
        analytics = PlatformAnalytics.objects.filter(date=today).first()
        
        # Company statistics
        context['total_companies'] = Company.objects.count()
        context['active_companies'] = Company.objects.filter(
            subscription_status='active'
        ).count()
        context['trial_companies'] = Company.objects.filter(
            subscription_status='trial'
        ).count()
        
        # Subscription statistics
        context['total_subscriptions'] = CompanySubscription.objects.filter(
            payment_status='active'
        ).count()
        
        # Revenue statistics
        context['mrr'] = CompanySubscription.objects.filter(
            payment_status='active',
            billing_cycle='monthly'
        ).aggregate(
            total=Sum('plan__monthly_price')
        )['total'] or 0
        
        # Recent companies
        context['recent_companies'] = Company.objects.order_by('-created_at')[:10]
        
        # Pending onboardings
        context['pending_onboardings'] = CompanyOnboarding.objects.filter(
            is_completed=False
        ).select_related('company')[:10]
        
        # Recent audit logs
        context['recent_logs'] = SystemAuditLog.objects.select_related(
            'admin_user', 'target_company'
        ).order_by('-created_at')[:20]
        
        # Platform config
        context['platform_config'] = PlatformConfiguration.get_config()
        
        # Today's analytics
        context['analytics'] = analytics
        
        return context


class CompanyListView(LoginRequiredMixin, SuperAdminRequiredMixin, ListView):
    """List all companies with filtering"""
    model = Company
    template_name = 'superAdmin/company_list.html'
    context_object_name = 'companies'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Company.objects.select_related(
            'subscription_details__plan'
        ).order_by('-created_at')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(subscription_status=status)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(company_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
        
        return queryset


class CompanyDetailView(LoginRequiredMixin, SuperAdminRequiredMixin, DetailView):
    """Detailed view of a company"""
    model = Company
    template_name = 'superAdmin/company_detail.html'
    context_object_name = 'company'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.object
        
        # Get subscription
        try:
            context['subscription'] = company.subscription_details
        except CompanySubscription.DoesNotExist:
            context['subscription'] = None
        
        # Get onboarding
        try:
            context['onboarding'] = company.onboarding
        except CompanyOnboarding.DoesNotExist:
            context['onboarding'] = None
        
        # User statistics
        context['total_users'] = CustomUser.objects.filter(company_profile=company).count()
        context['admins'] = CustomUser.objects.filter(company_profile=company, role='admin').count()
        context['clients'] = CustomUser.objects.filter(company_profile=company, role='client').count()
        context['marketers'] = CustomUser.objects.filter(company_profile=company, role='marketer').count()
        
        # Property statistics
        from estateApp.models import Estate, EstatePlot, PlotAllocation
        context['total_estates'] = Estate.objects.filter(company=company).count()
        context['total_plots'] = EstatePlot.objects.filter(estate__company=company).count()
        # Count allocations for this company (ensure correct relation name)
        context['allocated_plots'] = PlotAllocation.objects.filter(
            estate__company=company
        ).count()
        
        # Recent invoices
        context['recent_invoices'] = PlatformInvoice.objects.filter(
            company=company
        ).order_by('-issue_date')[:10]
        
        # Audit logs for this company
        context['audit_logs'] = SystemAuditLog.objects.filter(
            target_company=company
        ).order_by('-created_at')[:10]
        
        return context


class AnalyticsDashboardView(LoginRequiredMixin, SuperAdminRequiredMixin, TemplateView):
    """Platform-wide analytics dashboard"""
    template_name = 'superAdmin/analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range (last 30 days)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Get analytics data
        analytics_data = PlatformAnalytics.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date')
        
        context['analytics_data'] = analytics_data
        
        # Calculate trends
        if analytics_data.exists():
            latest = analytics_data.last()
            previous = analytics_data.first()
            
            context['company_growth'] = (
                (latest.total_companies - previous.total_companies) / previous.total_companies * 100
                if previous.total_companies > 0 else 0
            )
            
            context['user_growth'] = (
                (latest.total_users - previous.total_users) / previous.total_users * 100
                if previous.total_users > 0 else 0
            )
            
            context['revenue_growth'] = (
                (latest.total_revenue - previous.total_revenue) / previous.total_revenue * 100
                if previous.total_revenue > 0 else 0
            )
        
        # Latest metrics
        context['latest_metrics'] = analytics_data.last() if analytics_data.exists() else None
        
        return context


class SubscriptionManagementView(LoginRequiredMixin, SuperAdminRequiredMixin, ListView):
    """Manage all subscriptions"""
    model = CompanySubscription
    template_name = 'superAdmin/subscriptions.html'
    context_object_name = 'subscriptions'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = CompanySubscription.objects.select_related(
            'company', 'plan'
        ).order_by('-created_at')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(payment_status=status)
        
        # Filter by plan
        plan = self.request.GET.get('plan')
        if plan:
            queryset = queryset.filter(plan__tier=plan)
        
        return queryset


class InvoiceListView(LoginRequiredMixin, SuperAdminRequiredMixin, ListView):
    """List all invoices"""
    model = PlatformInvoice
    template_name = 'superAdmin/invoices.html'
    context_object_name = 'invoices'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = PlatformInvoice.objects.select_related('company').order_by('-issue_date')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset


class AuditLogView(LoginRequiredMixin, SuperAdminRequiredMixin, ListView):
    """View audit logs"""
    model = SystemAuditLog
    template_name = 'superAdmin/audit_logs.html'
    context_object_name = 'logs'
    paginate_by = 100
    
    def get_queryset(self):
        queryset = SystemAuditLog.objects.select_related(
            'admin_user', 'target_company'
        ).order_by('-created_at')
        
        # Filter by action type
        action = self.request.GET.get('action')
        if action:
            queryset = queryset.filter(action_type=action)
        
        return queryset


class FeatureFlagManagementView(LoginRequiredMixin, SuperAdminRequiredMixin, ListView):
    """Manage feature flags"""
    model = FeatureFlag
    template_name = 'superAdmin/feature_flags.html'
    context_object_name = 'flags'


class SystemSettingsView(LoginRequiredMixin, SuperAdminRequiredMixin, TemplateView):
    """Platform configuration settings"""
    template_name = 'superAdmin/settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['config'] = PlatformConfiguration.get_config()
        context['plans'] = SubscriptionPlan.objects.all()
        return context


@require_system_admin
def suspend_company(request, company_id):
    """Suspend a company"""
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        company.subscription_status = 'suspended'
        company.is_active = False
        company.save()
        
        # Log action
        SystemAuditLog.objects.create(
            user=request.user,
            action='COMPANY_SUSPENDED',
            resource=f"Company: {company.company_name}",
            status='SUCCESS',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={'company_id': company.id, 'company_name': company.company_name}
        )
        
        return JsonResponse({'status': 'success', 'message': 'Company suspended'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@require_system_admin
def activate_company(request, company_id):
    """Activate a suspended company"""
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        company.subscription_status = 'active'
        company.is_active = True
        company.save()
        
        # Log action
        SystemAuditLog.objects.create(
            user=request.user,
            action='COMPANY_ACTIVATED',
            resource=f"Company: {company.company_name}",
            status='SUCCESS',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={'company_id': company.id, 'company_name': company.company_name}
        )
        
        return JsonResponse({'status': 'success', 'message': 'Company activated'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


class AccessDeniedView(TemplateView):
    """Access denied page for non-super admins"""
    template_name = 'superAdmin/access_denied.html'
