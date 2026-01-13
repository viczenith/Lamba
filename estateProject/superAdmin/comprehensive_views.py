"""
Comprehensive SuperAdmin Management Dashboard
Complete system for managing all tenants, users, subscriptions, and platform operations
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, DetailView, UpdateView
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, Avg, F, Max, Min
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta, datetime
from decimal import Decimal
import json

from estateApp.models import (
    Company, CustomUser, Estate, PlotAllocation, 
    ClientUser, MarketerUser, Transaction
)
from estateApp.subscription_billing_models import SubscriptionBillingModel, BillingHistory
from estateApp.models import SubscriptionPlan
from .models import (
    PlatformConfiguration, SuperAdminUser, CompanySubscription,
    PlatformInvoice, PlatformAnalytics, SystemAuditLog, ConfigurationSettings
)


def is_system_admin(user):
    """Check if user is a system administrator"""
    return (
        user.is_authenticated and 
        (getattr(user, 'is_system_admin', False) or 
         getattr(user, 'is_superuser', False) or
         getattr(user, 'admin_level', 'none') == 'system')
    )


class SystemAdminRequiredMixin(UserPassesTestMixin):
    """Mixin to restrict access to system admins only"""
    login_url = '/super-admin/login/'
    
    def test_func(self):
        return is_system_admin(self.request.user)
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(f'{self.login_url}?next={self.request.get_full_path()}')
        messages.error(self.request, 'Access denied. System admin privileges required.')
        return redirect(self.login_url)


class SuperAdminDashboardView(SystemAdminRequiredMixin, TemplateView):
    """
    Main SuperAdmin Dashboard - Overview of entire platform
    Shows key metrics, recent activities, and system health
    """
    template_name = 'superadmin/comprehensive/main_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Time periods
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        year_ago = today - timedelta(days=365)
        
        # === COMPANY METRICS ===
        total_companies = Company.objects.count()
        active_companies = Company.objects.filter(
            subscription_status='active'
        ).count()
        trial_companies = Company.objects.filter(
            subscription_status='trial'
        ).count()
        suspended_companies = Company.objects.filter(
            subscription_status='suspended'
        ).count()
        
        # Companies by tier
        companies_by_tier = SubscriptionBillingModel.objects.values(
            'current_plan__tier'
        ).annotate(
            count=Count('id')
        )
        
        # New companies this month
        new_companies_month = Company.objects.filter(
            created_at__gte=month_ago
        ).count()
        
        # === USER METRICS ===
        total_users = CustomUser.objects.count()
        total_clients = CustomUser.objects.filter(role='client').count()
        total_marketers = CustomUser.objects.filter(role='marketer').count()
        total_admins = CustomUser.objects.filter(role__in=['admin', 'company_admin']).count()
        
        # Active users (logged in last 30 days)
        active_users = CustomUser.objects.filter(
            last_login__gte=month_ago
        ).count()
        
        # === REVENUE METRICS ===
        # Total revenue (all completed transactions)
        total_revenue = BillingHistory.objects.filter(
            state='completed'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Revenue this month
        monthly_revenue = BillingHistory.objects.filter(
            state='completed',
            created_at__gte=month_ago
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Revenue this year
        yearly_revenue = BillingHistory.objects.filter(
            state='completed',
            created_at__gte=year_ago
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # MRR (Monthly Recurring Revenue)
        mrr = SubscriptionBillingModel.objects.filter(
            status='active',
            billing_cycle='monthly'
        ).aggregate(
            total=Sum('monthly_amount')
        )['total'] or Decimal('0.00')
        
        # ARR (Annual Recurring Revenue)
        arr = mrr * 12
        
        # === SUBSCRIPTION METRICS ===
        active_subscriptions = SubscriptionBillingModel.objects.filter(
            status='active'
        ).count()
        
        trial_subscriptions = SubscriptionBillingModel.objects.filter(
            status='trial'
        ).count()
        
        expiring_soon = SubscriptionBillingModel.objects.filter(
            status='active',
            subscription_ends_at__lte=today + timedelta(days=7),
            subscription_ends_at__gt=today
        ).count()
        
        # === PROPERTY METRICS ===
        total_properties = Estate.objects.count()
        total_allocations = PlotAllocation.objects.count()
        total_transactions = Transaction.objects.count()
        
        # Transaction value
        total_transaction_value = Transaction.objects.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        # === GROWTH METRICS ===
        # Calculate growth rates
        last_month_start = month_ago - timedelta(days=30)
        
        companies_last_month = Company.objects.filter(
            created_at__gte=last_month_start,
            created_at__lt=month_ago
        ).count()
        
        company_growth = calculate_growth_rate(companies_last_month, new_companies_month)
        
        revenue_last_month = BillingHistory.objects.filter(
            state='completed',
            created_at__gte=last_month_start,
            created_at__lt=month_ago
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        revenue_growth = calculate_growth_rate(float(revenue_last_month), float(monthly_revenue))
        
        # === RECENT ACTIVITIES ===
        recent_companies = Company.objects.order_by('-created_at')[:10]
        recent_transactions = BillingHistory.objects.filter(
            state='completed'
        ).order_by('-created_at')[:10]
        
        # === SYSTEM HEALTH ===
        failed_payments = BillingHistory.objects.filter(
            state='failed',
            created_at__gte=week_ago
        ).count()
        
        pending_verifications = BillingHistory.objects.filter(
            state='verification_pending'
        ).count()
        
        # === TOP PERFORMERS ===
        # Get top companies by their billing history
        top_companies_by_revenue = []
        companies_with_billing = Company.objects.filter(
            subscription_details__isnull=False
        ).distinct()[:10]
        
        for company in companies_with_billing:
            try:
                revenue = BillingHistory.objects.filter(
                    subscription__company=company,
                    state='completed'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                top_companies_by_revenue.append({
                    'company': company,
                    'total_revenue': revenue
                })
            except Exception:
                pass
        
        # Sort by revenue and get top 5
        top_companies_by_revenue = sorted(
            top_companies_by_revenue, 
            key=lambda x: x['total_revenue'], 
            reverse=True
        )[:5]
        
        # Companies by plan distribution
        plan_distribution = []
        for tier_data in companies_by_tier:
            tier = tier_data['current_plan__tier']
            count = tier_data['count']
            if tier:
                plan_distribution.append({
                    'tier': tier.title(),
                    'count': count,
                    'percentage': round((count / total_companies * 100) if total_companies > 0 else 0, 1)
                })
        
        # === CHART DATA ===
        # Revenue trend (last 12 months)
        revenue_trend = []
        for i in range(11, -1, -1):
            month_start = today - timedelta(days=30 * (i + 1))
            month_end = today - timedelta(days=30 * i)
            revenue = BillingHistory.objects.filter(
                state='completed',
                created_at__gte=month_start,
                created_at__lt=month_end
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            revenue_trend.append({
                'month': month_start.strftime('%b %Y'),
                'revenue': float(revenue)
            })
        
        # Company signup trend (last 12 months)
        signup_trend = []
        for i in range(11, -1, -1):
            month_start = today - timedelta(days=30 * (i + 1))
            month_end = today - timedelta(days=30 * i)
            signups = Company.objects.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            ).count()
            
            signup_trend.append({
                'month': month_start.strftime('%b %Y'),
                'signups': signups
            })
        
        context.update({
            # Company metrics
            'total_companies': total_companies,
            'active_companies': active_companies,
            'trial_companies': trial_companies,
            'suspended_companies': suspended_companies,
            'new_companies_month': new_companies_month,
            'company_growth': company_growth,
            
            # User metrics
            'total_users': total_users,
            'total_clients': total_clients,
            'total_marketers': total_marketers,
            'total_admins': total_admins,
            'active_users': active_users,
            
            # Revenue metrics
            'total_revenue': total_revenue,
            'monthly_revenue': monthly_revenue,
            'yearly_revenue': yearly_revenue,
            'mrr': mrr,
            'arr': arr,
            'revenue_growth': revenue_growth,
            
            # Subscription metrics
            'active_subscriptions': active_subscriptions,
            'trial_subscriptions': trial_subscriptions,
            'expiring_soon': expiring_soon,
            
            # Property metrics
            'total_properties': total_properties,
            'total_allocations': total_allocations,
            'total_transactions': total_transactions,
            'total_transaction_value': total_transaction_value,
            
            # System health
            'failed_payments': failed_payments,
            'pending_verifications': pending_verifications,
            
            # Recent data
            'recent_companies': recent_companies,
            'recent_transactions': recent_transactions,
            'top_companies': top_companies_by_revenue,
            
            # Distributions
            'plan_distribution': plan_distribution,
            
            # Chart data
            'revenue_trend': json.dumps(revenue_trend),
            'signup_trend': json.dumps(signup_trend),
        })
        
        return context


class CompanyManagementView(SystemAdminRequiredMixin, ListView):
    """
    Manage all companies - List, filter, search, and perform actions
    """
    model = Company
    template_name = 'superadmin/comprehensive/company_management.html'
    context_object_name = 'companies'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Company.objects.select_related('subscription_details', 'subscription_details__plan').annotate(
            user_count=Count('users', distinct=True),
            property_count=Count('estates', distinct=True)
        ).order_by('-created_at')
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(company_name__icontains=search) |
                Q(email__icontains=search) |
                Q(slug__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(subscription_status=status)
        
        # Filter by plan tier
        tier = self.request.GET.get('tier', '')
        if tier:
            queryset = queryset.filter(billing__current_plan__tier=tier)
        
        # Filter by date
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filters for display
        context['search'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['tier_filter'] = self.request.GET.get('tier', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        # Get stats
        total_companies = Company.objects.count()
        filtered_count = self.get_queryset().count()
        
        context['total_companies'] = total_companies
        context['filtered_count'] = filtered_count
        context['subscription_plans'] = SubscriptionPlan.objects.filter(is_active=True)
        
        return context


class CompanyDetailView(SystemAdminRequiredMixin, DetailView):
    """
    Detailed view of a single company with all metrics and management options
    """
    model = Company
    template_name = 'superadmin/comprehensive/company_detail.html'
    context_object_name = 'company'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.object
        
        # Subscription info
        try:
            billing = company.billing
            context['billing'] = billing
            context['subscription'] = billing
        except:
            context['billing'] = None
            context['subscription'] = None
        
        # Users breakdown
        context['total_users'] = CustomUser.objects.filter(company_profile=company).count()
        context['admins'] = CustomUser.objects.filter(company_profile=company, role='admin').count()
        context['marketers'] = CustomUser.objects.filter(company_profile=company, role='marketer').count()
        context['clients'] = CustomUser.objects.filter(company_profile=company, role='client').count()
        
        # Properties and allocations
        context['total_properties'] = Estate.objects.filter(company=company).count()
        context['total_allocations'] = PlotAllocation.objects.filter(estate__company=company).count()
        
        # Financial metrics
        context['total_revenue'] = BillingHistory.objects.filter(
            billing__company=company,
            state='completed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        context['pending_payments'] = BillingHistory.objects.filter(
            billing__company=company,
            state='pending'
        ).count()
        
        # Recent billing history
        context['recent_transactions'] = BillingHistory.objects.filter(
            billing__company=company
        ).order_by('-created_at')[:10]
        
        # Recent users
        context['recent_users'] = CustomUser.objects.filter(
            company_profile=company
        ).order_by('-date_joined')[:10]
        
        # Activity timeline
        context['recent_properties'] = Estate.objects.filter(
            company=company
        ).order_by('-date_added')[:5]
        
        return context


class UserManagementView(SystemAdminRequiredMixin, ListView):
    """
    Manage clients and marketers only
    """
    model = CustomUser
    template_name = 'superadmin/comprehensive/user_management.html'
    context_object_name = 'users'
    paginate_by = 50
    
    def get_queryset(self):
        # Only show clients and marketers
        queryset = CustomUser.objects.filter(
            role__in=['client', 'marketer']
        ).select_related('company_profile').order_by('-date_joined')
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search)
            )
        
        # Filter by role
        role = self.request.GET.get('role', '')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by status
        is_active = self.request.GET.get('is_active', '')
        if is_active:
            queryset = queryset.filter(is_active=(is_active == 'true'))
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['search'] = self.request.GET.get('search', '')
        context['role_filter'] = self.request.GET.get('role', '')
        context['is_active_filter'] = self.request.GET.get('is_active', '')
        
        # Only count clients and marketers
        context['total_users'] = CustomUser.objects.filter(role__in=['client', 'marketer']).count()
        context['filtered_count'] = self.get_queryset().count()
        
        return context


class UserDetailView(SystemAdminRequiredMixin, DetailView):
    """
    Detailed view of a single user (client or marketer)
    """
    model = CustomUser
    template_name = 'superadmin/comprehensive/user_detail.html'
    context_object_name = 'user'
    pk_url_kwarg = 'pk'
    
    def get_queryset(self):
        # Only allow viewing clients and marketers
        return CustomUser.objects.filter(role__in=['client', 'marketer'])
    
    def get_context_data(self, **kwargs):
        from estateApp.models import Transaction, MarketerCommission, MarketerAffiliation, PlotAllocation
        from django.db.models import Sum
        from datetime import datetime
        
        context = super().get_context_data(**kwargs)
        user = self.object
        
        # User stats
        context['total_logins'] = user.last_login is not None
        context['account_age_days'] = (timezone.now().date() - user.date_joined.date()).days
        
        # Determine how user was created
        # Check if user registered through public signup form or was created by company admin
        if user.is_system_admin or user.admin_level == 'system':
            # SuperAdmin account
            context['creation_method'] = 'system'
            context['creation_source'] = 'System Administrator Account'
        elif user.admin_level == 'company' and user.company_profile:
            # Company admin - likely registered their own company
            context['creation_method'] = 'self'
            context['creation_source'] = f'Self-registered via Company Registration (Owner of {user.company_profile.company_name})'
        elif not user.company_profile:
            # No company affiliation - definitely self-registered via public form
            context['creation_method'] = 'self'
            context['creation_source'] = 'Self-registered via Public Signup Form (No company affiliation)'
        else:
            # Has company but not admin - check if they're the first user (company owner) or created by admin
            # If user's date_joined is very close to company's created_at, they likely created the company
            if user.company_profile.created_at and abs((user.date_joined - user.company_profile.created_at).total_seconds()) < 60:
                context['creation_method'] = 'self'
                context['creation_source'] = f'Self-registered via Public Signup Form (Affiliated with {user.company_profile.company_name})'
            else:
                # User joined after company was created - likely created by company admin
                context['creation_method'] = 'company'
                context['creation_source'] = f'Created by {user.company_profile.company_name} Company Admin'
        
        # Company info
        context['company'] = None
        context['primary_company_data'] = None
        if user.company_profile:
            context['company'] = user.company_profile
            
            # Calculate transaction data for primary company (for marketers)
            if user.role == 'marketer':
                primary_company = user.company_profile
                
                # Get actual transaction data for primary company
                transactions = Transaction.objects.filter(
                    marketer=user,
                    company=primary_company
                )
                
                # Calculate properties sold
                properties_sold = transactions.count()
                
                # Calculate total sales value
                total_sales = transactions.aggregate(
                    total=Sum('total_amount')
                )['total'] or 0
                
                # Get commission rate
                today = datetime.now().date()
                commission_obj = MarketerCommission.objects.filter(
                    marketer_id=user.id,
                    company=primary_company,
                    effective_date__lte=today
                ).order_by('-effective_date').first()
                
                commission_rate = commission_obj.rate if commission_obj else 0
                
                # Calculate commissions earned
                commissions_earned = total_sales * (commission_rate / 100) if commission_rate else 0
                
                # Get affiliation date (when they joined this company)
                try:
                    affiliation = MarketerAffiliation.objects.filter(
                        marketer=user,
                        company=primary_company
                    ).first()
                    date_joined = affiliation.date_affiliated if affiliation else user.date_joined
                    commission_tier = affiliation.get_commission_tier_display() if affiliation else "N/A"
                    commissions_paid = affiliation.total_commissions_paid if affiliation else 0
                except:
                    date_joined = user.date_joined
                    commissions_paid = 0
                
                context['primary_company_data'] = {
                    'properties_sold': properties_sold,
                    'total_sales': total_sales,
                    'commission_rate': commission_rate,
                    'commissions_earned': commissions_earned,
                    'commissions_paid': commissions_paid,
                    'date_joined': date_joined,
                }
        
        # Additional company affiliations (for marketers)
        context['affiliated_companies'] = []
        if user.role == 'marketer':
            # Get all company affiliations for this marketer
            affiliations = MarketerAffiliation.objects.filter(
                marketer=user
            ).select_related('company').order_by('-date_affiliated')
            
            # Calculate real transaction data for each affiliation
            enriched_affiliations = []
            for affiliation in affiliations:
                # Get actual transaction data for this company
                transactions = Transaction.objects.filter(
                    marketer=user,
                    company=affiliation.company
                )
                
                # Calculate properties sold (count of transactions)
                properties_sold = transactions.count()
                
                # Calculate total sales value
                total_sales = transactions.aggregate(
                    total=Sum('total_amount')
                )['total'] or 0
                
                # Get actual commission rate from MarketerCommission
                today = datetime.now().date()
                commission_obj = MarketerCommission.objects.filter(
                    marketer_id=user.id,
                    company=affiliation.company,
                    effective_date__lte=today
                ).order_by('-effective_date').first()
                
                actual_commission_rate = commission_obj.rate if commission_obj else affiliation.commission_rate
                
                # Calculate commissions earned (from total sales * commission rate)
                commissions_earned = total_sales * (actual_commission_rate / 100) if actual_commission_rate else 0
                
                # Add calculated fields to affiliation object
                affiliation.calculated_properties_sold = properties_sold
                affiliation.calculated_total_sales = total_sales
                affiliation.calculated_commission_rate = actual_commission_rate
                affiliation.calculated_commissions_earned = commissions_earned
                
                enriched_affiliations.append(affiliation)
            
            context['affiliated_companies'] = enriched_affiliations
        
        # Role-specific data
        if user.role == 'marketer':
            # Marketer stats
            try:
                marketer = MarketerUser.objects.get(pk=user.pk)
                context['marketer_profile'] = marketer
                context['total_clients_referred'] = ClientUser.objects.filter(assigned_marketer=marketer).count()
            except MarketerUser.DoesNotExist:
                context['marketer_profile'] = None
                context['total_clients_referred'] = 0
        
        elif user.role == 'client':
            # Client stats
            try:
                from estateApp.models import CompanyClientProfile
                
                client = ClientUser.objects.get(pk=user.pk)
                context['client_profile'] = client
                
                # Get primary company from context
                primary_company = context.get('company')
                
                # Get client transactions
                context['total_transactions'] = Transaction.objects.filter(client=client).count()
                context['total_investment'] = Transaction.objects.filter(
                    client=client
                ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
                
                # Get client properties
                context['properties_owned'] = PlotAllocation.objects.filter(client=client).count()
                
                # Get all companies this client is affiliated with (excluding primary company)
                client_affiliations_query = CompanyClientProfile.objects.filter(
                    client=client
                ).select_related('company')
                
                # Exclude primary company if it exists
                if primary_company:
                    client_affiliations_query = client_affiliations_query.exclude(company=primary_company)
                
                client_affiliations = client_affiliations_query
                
                # Enrich each affiliation with transaction data
                affiliated_companies_data = []
                for affiliation in client_affiliations:
                    # Get transactions for this specific company
                    company_transactions = Transaction.objects.filter(
                        client=client,
                        company=affiliation.company
                    )
                    
                    # Calculate metrics
                    total_investment = company_transactions.aggregate(
                        total=Sum('total_amount')
                    )['total'] or Decimal('0.00')
                    
                    transactions_count = company_transactions.count()
                    
                    # Get properties from this company
                    properties_owned = PlotAllocation.objects.filter(
                        client=client,
                        estate__company=affiliation.company
                    ).count()
                    
                    # Add calculated fields to affiliation
                    affiliation.calculated_total_investment = total_investment
                    affiliation.calculated_transactions_count = transactions_count
                    affiliation.calculated_properties_owned = properties_owned
                    
                    affiliated_companies_data.append(affiliation)
                
                context['client_affiliated_companies'] = affiliated_companies_data
                
                # Calculate data for primary company if exists
                if primary_company:
                    primary_transactions = Transaction.objects.filter(
                        client=client,
                        company=primary_company
                    )
                    
                    # Get primary company client profile for UID
                    primary_profile = CompanyClientProfile.objects.filter(
                        client=client,
                        company=primary_company
                    ).first()
                    
                    context['primary_company_data'] = {
                        'total_investment': primary_transactions.aggregate(
                            total=Sum('total_amount')
                        )['total'] or Decimal('0.00'),
                        'transactions_count': primary_transactions.count(),
                        'properties_owned': PlotAllocation.objects.filter(
                            client=client,
                            estate__company=primary_company
                        ).count(),
                        'date_joined': user.date_joined or user.date_registered,
                        'client_uid': primary_profile.company_client_uid if primary_profile else 'N/A',
                    }
                
            except ClientUser.DoesNotExist:
                context['client_profile'] = None
                context['total_transactions'] = 0
                context['total_investment'] = Decimal('0.00')
                context['properties_owned'] = 0
                context['client_affiliated_companies'] = []
        
        # Recent activity (if client)
        if user.role == 'client':
            try:
                client = ClientUser.objects.get(pk=user.pk)
                context['recent_transactions'] = Transaction.objects.filter(
                    client=client
                ).order_by('-created_at')[:10]
                context['recent_allocations'] = PlotAllocation.objects.filter(
                    client=client
                ).order_by('-date_allocated')[:10]
            except ClientUser.DoesNotExist:
                context['recent_transactions'] = []
                context['recent_allocations'] = []
        
        return context


class SubscriptionManagementView(SystemAdminRequiredMixin, ListView):
    """
    Manage all subscriptions across the platform
    """
    model = SubscriptionBillingModel
    template_name = 'superadmin/comprehensive/subscription_management.html'
    context_object_name = 'subscriptions'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = SubscriptionBillingModel.objects.select_related(
            'company', 'current_plan'
        ).order_by('-created_at')
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by plan
        plan = self.request.GET.get('plan', '')
        if plan:
            queryset = queryset.filter(current_plan__tier=plan)
        
        # Filter by billing cycle
        cycle = self.request.GET.get('cycle', '')
        if cycle:
            queryset = queryset.filter(billing_cycle=cycle)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['status_filter'] = self.request.GET.get('status', '')
        context['plan_filter'] = self.request.GET.get('plan', '')
        context['cycle_filter'] = self.request.GET.get('cycle', '')
        
        # Stats
        context['total_subscriptions'] = SubscriptionBillingModel.objects.count()
        context['active_count'] = SubscriptionBillingModel.objects.filter(status='active').count()
        context['trial_count'] = SubscriptionBillingModel.objects.filter(status='trial').count()
        context['expired_count'] = SubscriptionBillingModel.objects.filter(status='expired').count()
        
        # MRR and ARR
        context['mrr'] = SubscriptionBillingModel.objects.filter(
            status='active', billing_cycle='monthly'
        ).aggregate(total=Sum('monthly_amount'))['total'] or Decimal('0.00')
        
        context['arr'] = context['mrr'] * 12
        
        context['subscription_plans'] = SubscriptionPlan.objects.filter(is_active=True)
        
        return context


class BillingManagementView(SystemAdminRequiredMixin, ListView):
    """
    Manage all billing transactions and invoices
    """
    model = BillingHistory
    template_name = 'superadmin/comprehensive/billing_management.html'
    context_object_name = 'transactions'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = BillingHistory.objects.select_related(
            'billing__company'
        ).order_by('-created_at')
        
        # Filter by state
        state = self.request.GET.get('state', '')
        if state:
            queryset = queryset.filter(state=state)
        
        # Filter by payment method
        method = self.request.GET.get('method', '')
        if method:
            queryset = queryset.filter(payment_method=method)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['state_filter'] = self.request.GET.get('state', '')
        context['method_filter'] = self.request.GET.get('method', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        queryset = self.get_queryset()
        
        # Calculate totals
        context['total_transactions'] = queryset.count()
        context['total_amount'] = queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        context['completed_amount'] = queryset.filter(state='completed').aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')
        context['pending_amount'] = queryset.filter(state='pending').aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')
        
        return context


class AnalyticsView(SystemAdminRequiredMixin, TemplateView):
    """
    Advanced analytics and reporting dashboard
    """
    template_name = 'superadmin/analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Time periods
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)
        last_90_days = today - timedelta(days=90)
        last_year = today - timedelta(days=365)
        
        # Revenue analytics
        revenue_by_plan = BillingHistory.objects.filter(
            state='completed'
        ).values('billing__current_plan__name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        # User growth
        user_growth = []
        for i in range(12, 0, -1):
            month = today - timedelta(days=30 * i)
            count = CustomUser.objects.filter(date_joined__month=month.month, date_joined__year=month.year).count()
            user_growth.append({'month': month.strftime('%b'), 'count': count})
        
        # Company churn analysis
        churned_companies = SubscriptionBillingModel.objects.filter(
            status='cancelled',
            updated_at__gte=last_90_days
        ).count()
        
        total_companies = Company.objects.filter(created_at__lte=last_90_days).count()
        churn_rate = (churned_companies / total_companies * 100) if total_companies > 0 else 0
        
        # Average revenue per customer (ARPC)
        active_companies_count = SubscriptionBillingModel.objects.filter(status='active').count()
        total_mrr = SubscriptionBillingModel.objects.filter(
            status='active', billing_cycle='monthly'
        ).aggregate(total=Sum('monthly_amount'))['total'] or Decimal('0.00')
        arpc = (total_mrr / active_companies_count) if active_companies_count > 0 else 0
        
        # Lifetime value (LTV) estimation
        avg_subscription_length = 12  # months (estimate)
        ltv = float(arpc) * avg_subscription_length
        
        context.update({
            'revenue_by_plan': list(revenue_by_plan),
            'user_growth': user_growth,
            'churn_rate': round(churn_rate, 2),
            'arpc': arpc,
            'ltv': ltv,
        })
        
        return context


# === AJAX/API ENDPOINTS ===

@login_required
def company_action(request):
    """
    Perform actions on companies (activate, suspend, delete, etc.)
    """
    if not is_system_admin(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        data = json.loads(request.body)
        company_id = data.get('company_id')
        action = data.get('action')
        
        company = Company.objects.get(id=company_id)
        
        if action == 'activate':
            company.subscription_status = 'active'
            company.is_active = True
            company.save()
            message = f'{company.company_name} activated successfully'
            
        elif action == 'suspend':
            company.subscription_status = 'suspended'
            company.save()
            message = f'{company.company_name} suspended successfully'
            
        elif action == 'delete':
            company_name = company.company_name
            company.delete()
            message = f'{company_name} deleted successfully'
            
        elif action == 'reset_trial':
            billing = company.billing
            billing.status = 'trial'
            billing.trial_started_at = timezone.now()
            billing.trial_ends_at = timezone.now() + timedelta(days=14)
            billing.save()
            message = f'Trial period reset for {company.company_name}'
            
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        return JsonResponse({'success': True, 'message': message})
        
    except Company.DoesNotExist:
        return JsonResponse({'error': 'Company not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def subscription_action(request):
    """
    Perform actions on subscriptions
    """
    if not is_system_admin(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        data = json.loads(request.body)
        subscription_id = data.get('subscription_id')
        action = data.get('action')
        
        subscription = SubscriptionBillingModel.objects.get(id=subscription_id)
        
        if action == 'extend':
            days = int(data.get('days', 30))
            if subscription.subscription_ends_at:
                subscription.subscription_ends_at += timedelta(days=days)
            else:
                subscription.subscription_ends_at = timezone.now() + timedelta(days=days)
            subscription.save()
            message = f'Subscription extended by {days} days'
            
        elif action == 'cancel':
            subscription.status = 'cancelled'
            subscription.auto_renew = False
            subscription.save()
            message = 'Subscription cancelled'
            
        elif action == 'reactivate':
            subscription.status = 'active'
            subscription.save()
            message = 'Subscription reactivated'
            
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        return JsonResponse({'success': True, 'message': message})
        
    except SubscriptionBillingModel.DoesNotExist:
        return JsonResponse({'error': 'Subscription not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_platform_stats(request):
    """
    Get real-time platform statistics for dashboard widgets
    """
    if not is_system_admin(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    stats = {
        'companies': {
            'total': Company.objects.count(),
            'active': Company.objects.filter(subscription_status='active').count(),
            'new_today': Company.objects.filter(created_at__date=today).count(),
        },
        'users': {
            'total': CustomUser.objects.count(),
            'active_today': CustomUser.objects.filter(last_login__date=today).count(),
        },
        'revenue': {
            'today': float(BillingHistory.objects.filter(
                state='completed', created_at__date=today
            ).aggregate(total=Sum('amount'))['total'] or 0),
            'week': float(BillingHistory.objects.filter(
                state='completed', created_at__gte=week_ago
            ).aggregate(total=Sum('amount'))['total'] or 0),
        },
        'system': {
            'failed_payments': BillingHistory.objects.filter(
                state='failed', created_at__gte=week_ago
            ).count(),
            'pending_verifications': BillingHistory.objects.filter(
                state='verification_pending'
            ).count(),
        }
    }
    
    return JsonResponse(stats)


def calculate_growth_rate(old_value, new_value):
    """Calculate percentage growth rate"""
    if old_value == 0:
        return 100 if new_value > 0 else 0
    return round(((new_value - old_value) / old_value) * 100, 1)


# ==================== PLAN & BILLING MANAGEMENT API ====================

@login_required
def get_plan_details(request, plan_id):
    """Get details of a specific subscription plan"""
    if not is_system_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
        return JsonResponse({
            'success': True,
            'plan': {
                'id': plan.id,
                'name': plan.name,
                'tier': plan.tier,
                'description': plan.description,
                'monthly_price': float(plan.monthly_price),
                'annual_price': float(plan.annual_price),
                'max_estates': plan.max_estates,
                'max_allocations': plan.max_allocations,
                'max_clients': plan.max_clients,
                'max_affiliates': plan.max_affiliates,
                'is_active': plan.is_active
            }
        })
    except SubscriptionPlan.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Plan not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def create_plan(request):
    """Create a new subscription plan"""
    if not is_system_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        # Get form data
        name = request.POST.get('name')
        tier = request.POST.get('tier')
        description = request.POST.get('description', '')
        monthly_price = request.POST.get('monthly_price')
        annual_price = request.POST.get('annual_price')
        max_estates = request.POST.get('max_estates') or None
        max_allocations = request.POST.get('max_allocations') or None
        max_clients = request.POST.get('max_clients') or None
        max_affiliates = request.POST.get('max_affiliates') or None
        
        # Validate required fields
        if not all([name, tier, monthly_price, annual_price]):
            return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
        
        # Create plan
        plan = SubscriptionPlan.objects.create(
            name=name,
            tier=tier,
            description=description,
            monthly_price=Decimal(monthly_price),
            annual_price=Decimal(annual_price),
            max_estates=int(max_estates) if max_estates else None,
            max_allocations=int(max_allocations) if max_allocations else None,
            max_clients=int(max_clients) if max_clients else None,
            max_affiliates=int(max_affiliates) if max_affiliates else None,
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Plan created successfully',
            'plan_id': plan.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def update_plan(request, plan_id):
    """Update an existing subscription plan"""
    if not is_system_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
        
        # Update fields
        plan.name = request.POST.get('name', plan.name)
        plan.tier = request.POST.get('tier', plan.tier)
        plan.description = request.POST.get('description', plan.description)
        
        monthly_price = request.POST.get('monthly_price')
        if monthly_price:
            plan.monthly_price = Decimal(monthly_price)
        
        annual_price = request.POST.get('annual_price')
        if annual_price:
            plan.annual_price = Decimal(annual_price)
        
        max_estates = request.POST.get('max_estates')
        plan.max_estates = int(max_estates) if max_estates else None
        
        max_allocations = request.POST.get('max_allocations')
        plan.max_allocations = int(max_allocations) if max_allocations else None
        
        max_clients = request.POST.get('max_clients')
        plan.max_clients = int(max_clients) if max_clients else None
        
        max_affiliates = request.POST.get('max_affiliates')
        plan.max_affiliates = int(max_affiliates) if max_affiliates else None
        
        plan.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Plan updated successfully'
        })
    except SubscriptionPlan.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Plan not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def toggle_plan_status(request, plan_id):
    """Toggle plan active/inactive status"""
    if not is_system_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
        
        # Get status from request
        data = json.loads(request.body)
        is_active = data.get('is_active', not plan.is_active)
        
        plan.is_active = is_active
        plan.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Plan {"activated" if is_active else "deactivated"} successfully',
            'is_active': is_active
        })
    except SubscriptionPlan.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Plan not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def delete_plan(request, plan_id):
    """Delete a subscription plan (only if no active subscriptions)"""
    if not is_system_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
        
        # Check if plan has active subscriptions
        active_subscriptions = SubscriptionBillingModel.objects.filter(
            current_plan=plan,
            status='active'
        ).count()
        
        if active_subscriptions > 0:
            return JsonResponse({
                'success': False,
                'error': f'Cannot delete plan with {active_subscriptions} active subscription(s)'
            }, status=400)
        
        plan_name = plan.name
        plan.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Plan "{plan_name}" deleted successfully'
        })
    except SubscriptionPlan.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Plan not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def get_billing_settings(request):
    """Get billing configuration settings"""
    if not is_system_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        # Get or create configuration settings
        config, created = ConfigurationSettings.objects.get_or_create(
            key='billing_settings',
            defaults={
                'value': {
                    'paystack_public_key': '',
                    'paystack_secret_key': '',
                    'bank_name': 'First Bank of Nigeria',
                    'account_number': '3124567890',
                    'account_name': 'Real Estate MS Limited'
                }
            }
        )
        
        settings = config.value
        
        return JsonResponse({
            'success': True,
            'settings': settings
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def save_billing_settings(request):
    """Save billing configuration settings"""
    if not is_system_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        settings = {
            'paystack_public_key': data.get('paystack_public_key', ''),
            'paystack_secret_key': data.get('paystack_secret_key', ''),
            'bank_name': data.get('bank_name', ''),
            'account_number': data.get('account_number', ''),
            'account_name': data.get('account_name', '')
        }
        
        # Update or create configuration
        config, created = ConfigurationSettings.objects.update_or_create(
            key='billing_settings',
            defaults={'value': settings}
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Billing settings saved successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
