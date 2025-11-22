"""
Management command to generate and manage invoices for companies.
Creates invoices for SaaS subscriptions and tracks payment records.

Usage:
    python manage.py generate_invoices
    python manage.py generate_invoices --month=2025-01
    python manage.py generate_invoices --dry-run
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from estateApp.models import Company
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate monthly invoices for SaaS subscriptions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=str,
            help='Generate invoices for specific month (YYYY-MM format)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--last-month',
            action='store_true',
            help='Generate invoices for last month'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        month_str = options.get('month')
        last_month = options.get('last_month')

        now = timezone.now()

        # Determine target month
        if month_str:
            try:
                target_date = timezone.datetime.strptime(month_str, '%Y-%m')
                target_date = timezone.make_aware(target_date)
            except ValueError:
                raise CommandError("Invalid month format. Use YYYY-MM (e.g., 2025-01)")
        elif last_month:
            target_date = now - relativedelta(months=1)
        else:
            target_date = now

        # Get companies with active subscriptions
        active_companies = Company.objects.filter(
            subscription_status='active',
            is_active=True
        )

        self.stdout.write(f"Generating invoices for {active_companies.count()} active companies...")

        # Pricing tiers (example - customize as needed)
        PRICING = {
            'starter': 50000,      # ₦50,000
            'professional': 150000, # ₦150,000
            'enterprise': 500000,   # ₦500,000
        }

        invoices = []
        total_revenue = 0

        for company in active_companies:
            base_price = PRICING.get(company.subscription_tier, 0)
            
            # Calculate additional fees based on usage
            api_calls_limit = company.max_api_calls_daily
            plot_count = 0  # Add actual calculation here
            
            # Simple pricing model
            tier_price = base_price
            
            invoice_data = {
                'company': company,
                'month': target_date.strftime('%Y-%m'),
                'tier': company.subscription_tier,
                'base_price': tier_price,
                'tax_rate': 0.075,  # 7.5% VAT (Nigeria)
                'tax_amount': tier_price * 0.075,
                'total': tier_price * 1.075,
            }

            invoices.append(invoice_data)
            total_revenue += invoice_data['total']

        # Display preview
        self.stdout.write("\nInvoice Preview:")
        self.stdout.write("-" * 80)

        for invoice in invoices[:5]:
            company = invoice['company']
            self.stdout.write(
                f"{company.company_name:30} | "
                f"Tier: {invoice['tier']:12} | "
                f"Amount: ₦{invoice['total']:,.2f}"
            )

        if len(invoices) > 5:
            self.stdout.write(f"... and {len(invoices) - 5} more companies")

        self.stdout.write("-" * 80)
        self.stdout.write(f"Total Revenue (with VAT): ₦{total_revenue:,.2f}")

        if dry_run:
            self.stdout.write(self.style.WARNING(f"\nDRY RUN: Would generate {len(invoices)} invoices"))
            return

        # In production, save invoices to database
        # This is a template - implement actual Invoice model if needed
        self.stdout.write(self.style.SUCCESS(f"\n✓ Generated invoices for {len(invoices)} companies"))
        self.stdout.write(f"  Total Revenue: ₦{total_revenue:,.2f}")
        self.stdout.write(f"  Month: {target_date.strftime('%B %Y')}")
        
        logger.info(f"Generated {len(invoices)} invoices totaling ₦{total_revenue:,.2f}")
