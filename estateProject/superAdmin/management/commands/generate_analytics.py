"""
Management command to generate daily platform analytics
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum, Count
from decimal import Decimal

from superAdmin.models import PlatformAnalytics, CompanySubscription
from estateApp.models import Company, CustomUser, EstatePlot, PlotAllocation


class Command(BaseCommand):
    help = 'Generate daily platform analytics snapshot'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to generate analytics for (YYYY-MM-DD). Defaults to today.'
        )
    
    def handle(self, *args, **options):
        # Get date
        if options.get('date'):
            from datetime import datetime
            date = datetime.strptime(options['date'], '%Y-%m-%d').date()
        else:
            date = timezone.now().date()
        
        self.stdout.write(f'Generating analytics for {date}...')
        
        # Check if analytics already exist
        analytics, created = PlatformAnalytics.objects.get_or_create(
            date=date,
            defaults={}
        )
        
        # Company metrics
        analytics.total_companies = Company.objects.count()
        analytics.active_companies = Company.objects.filter(subscription_status='active').count()
        analytics.trial_companies = Company.objects.filter(subscription_status='trial').count()
        analytics.suspended_companies = Company.objects.filter(subscription_status='suspended').count()
        
        # New companies today
        analytics.new_companies_today = Company.objects.filter(
            created_at__date=date
        ).count()
        
        # User metrics
        analytics.total_users = CustomUser.objects.count()
        analytics.total_clients = CustomUser.objects.filter(role='client').count()
        analytics.total_marketers = CustomUser.objects.filter(role='marketer').count()
        analytics.total_admins = CustomUser.objects.filter(role='admin').count()
        
        # New users today
        analytics.new_users_today = CustomUser.objects.filter(
            date_joined__date=date
        ).count()
        
        # Property metrics
        analytics.total_properties = EstatePlot.objects.count()
        analytics.total_plots_allocated = PlotAllocation.objects.count()
        analytics.properties_sold_today = PlotAllocation.objects.filter(
            date_assigned__date=date
        ).count()
        
        # Financial metrics - MRR (Monthly Recurring Revenue)
        mrr = CompanySubscription.objects.filter(
            payment_status='active',
            billing_cycle='monthly'
        ).aggregate(
            total=Sum('plan__monthly_price')
        )['total'] or Decimal('0')
        
        analytics.mrr = mrr
        analytics.arr = mrr * 12  # Annual Recurring Revenue
        
        # Revenue today (from payments)
        # TODO: Implement when payment tracking is added
        analytics.revenue_today = Decimal('0')
        
        # Total revenue
        analytics.total_revenue = CompanySubscription.objects.filter(
            payment_status='active'
        ).aggregate(
            total=Sum('amount_paid')
        )['total'] or Decimal('0')
        
        # Commission metrics
        # TODO: Calculate from MarketerEarnedCommission model
        analytics.platform_commission_earned = Decimal('0')
        analytics.marketer_commission_paid = Decimal('0')
        
        # System metrics
        # TODO: Track API calls and storage
        analytics.api_calls_today = 0
        analytics.storage_used_gb = Decimal('0')
        
        analytics.save()
        
        action = 'Created' if created else 'Updated'
        self.stdout.write(
            self.style.SUCCESS(
                f'{action} analytics for {date}: '
                f'{analytics.total_companies} companies, '
                f'{analytics.total_users} users, '
                f'MRR: ₦{analytics.mrr:,.2f}'
            )
        )
