"""
Management command to create demo billing transactions for testing.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import uuid

from estateApp.models import Company
from superAdmin.models import SubscriptionPlan
from estateApp.subscription_billing_models import (
    SubscriptionBillingModel, BillingHistory
)


class Command(BaseCommand):
    help = 'Create demo billing transactions for testing the receipt and billing history features'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company',
            type=str,
            help='Company name to create transactions for (defaults to first company with subscription)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Creating demo billing transactions...'))
        
        # Find a company with an active subscription
        company_name = options.get('company')
        
        if company_name:
            companies = Company.objects.filter(company_name__icontains=company_name)
        else:
            companies = Company.objects.all()
        
        target_company = None
        billing = None
        
        for company in companies:
            # Find a billing record for this company
            try:
                bill = company.billing
                if bill:
                    target_company = company
                    billing = bill
                    break
            except SubscriptionBillingModel.DoesNotExist:
                continue
        
        if not target_company:
            self.stdout.write(self.style.WARNING('No company with billing record found. Creating one...'))
            # Create billing record for the first company
            target_company = Company.objects.first()
            if not target_company:
                self.stdout.write(self.style.ERROR('No companies found in database.'))
                return
            
            # Get a plan
            plan = SubscriptionPlan.objects.filter(tier='professional').first()
            if not plan:
                plan = SubscriptionPlan.objects.first()
            
            # Create billing record
            billing, created = SubscriptionBillingModel.objects.get_or_create(
                company=target_company,
                defaults={
                    'status': 'active',
                    'billing_cycle': 'monthly',
                    'payment_method': 'paystack',
                    'next_billing_date': timezone.now().date() + timedelta(days=30),
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created billing record for {target_company.company_name}'))
        
        self.stdout.write(self.style.NOTICE(f'Using company: {target_company.company_name}'))
        
        # Create demo transactions
        demo_transactions = [
            {
                'transaction_type': 'charge',
                'state': 'completed',
                'amount': 100000.00,  # Professional plan
                'description': 'Professional Plan - Monthly Subscription',
                'days_ago': 0,
                'paid': True
            },
            {
                'transaction_type': 'charge',
                'state': 'completed',
                'amount': 100000.00,
                'description': 'Professional Plan - Monthly Subscription Renewal',
                'days_ago': 30,
                'paid': True
            },
            {
                'transaction_type': 'charge',
                'state': 'completed',
                'amount': 70000.00,
                'description': 'Starter Plan - Monthly Subscription (Upgraded from)',
                'days_ago': 60,
                'paid': True
            },
            {
                'transaction_type': 'refund',
                'state': 'completed',
                'amount': 20000.00,
                'description': 'Proration Refund - Plan Upgrade Credit',
                'days_ago': 30,
                'paid': True
            },
        ]
        
        created_count = 0
        
        for idx, tx_data in enumerate(demo_transactions):
            billing_date = timezone.now() - timedelta(days=tx_data['days_ago'])
            due_date = (billing_date + timedelta(days=7)).date()
            
            # Generate unique IDs
            transaction_id = f"TX-{uuid.uuid4().hex[:12].upper()}"
            invoice_number = f"INV-{target_company.id}-{billing_date.strftime('%Y%m')}-{idx+1:04d}"
            
            # Check if invoice number exists
            existing = BillingHistory.objects.filter(invoice_number=invoice_number).first()
            if existing:
                invoice_number = f"INV-{target_company.id}-{billing_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
            
            # Create the transaction
            try:
                tx = BillingHistory.objects.create(
                    billing=billing,
                    transaction_type=tx_data['transaction_type'],
                    state=tx_data['state'],
                    amount=tx_data['amount'],
                    currency='NGN',
                    description=tx_data['description'],
                    transaction_id=transaction_id,
                    billing_date=billing_date,
                    due_date=due_date,
                    paid_date=billing_date if tx_data['paid'] else None,
                    invoice_number=invoice_number,
                    payment_method='paystack' if idx % 2 == 0 else 'stripe'
                )
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Created: {invoice_number} - NGN {tx_data['amount']:,.2f} ({tx_data['description'][:40]})"
                ))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Warning: {e}"))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Created {created_count} demo transactions for {target_company.company_name}'))
        self.stdout.write(self.style.NOTICE(f'Go to Subscription & Billing tab to view and test receipt downloads'))
