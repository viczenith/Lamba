"""
Management command to process pending marketer commissions.
Approves and marks commissions as paid based on company approval settings.

Usage:
    python manage.py process_commissions
    python manage.py process_commissions --company=1
    python manage.py process_commissions --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Sum, Q
from estateApp.models import MarketerEarnedCommission, MarketerAffiliation, Company
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process pending marketer commissions (approve and mark as paid)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company',
            type=int,
            help='Process commissions for a specific company ID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--days-old',
            type=int,
            default=7,
            help='Only process commissions older than N days (default: 7)'
        )

    def handle(self, *args, **options):
        company_id = options.get('company')
        dry_run = options.get('dry_run')
        days_old = options.get('days_old')

        # Filter commissions
        cutoff_date = timezone.now() - timezone.timedelta(days=days_old)
        
        query = MarketerEarnedCommission.objects.filter(
            status='pending',
            created_at__lte=cutoff_date
        )

        if company_id:
            query = query.filter(affiliation__company_id=company_id)
            company = Company.objects.get(id=company_id)
            self.stdout.write(f"Processing commissions for {company.company_name}...")
        else:
            self.stdout.write("Processing commissions across all companies...")

        pending_count = query.count()
        if pending_count == 0:
            self.stdout.write(self.style.WARNING("No pending commissions to process."))
            return

        self.stdout.write(f"Found {pending_count} pending commissions older than {days_old} days.")

        if dry_run:
            total_amount = query.aggregate(
                total=Sum('commission_amount')
            )['total'] or 0
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would approve ₦{total_amount:,.2f}"))
            
            # Show breakdown by company
            for commission in query[:5]:
                self.stdout.write(f"  - {commission.affiliation.company.company_name}: ₦{commission.commission_amount:,.2f}")
            if query.count() > 5:
                self.stdout.write(f"  ... and {query.count() - 5} more")
            return

        # Process commissions
        approved_count = 0
        paid_count = 0
        total_approved = 0
        total_paid = 0

        for commission in query:
            try:
                # Approve if pending
                if commission.status == 'pending':
                    commission.approve()
                    approved_count += 1
                    total_approved += commission.commission_amount

                # Mark as paid
                if commission.status == 'approved':
                    payment_ref = f"PAYOUT-{commission.affiliation.company_id}-{commission.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
                    commission.mark_as_paid(payment_ref)
                    paid_count += 1
                    total_paid += commission.commission_amount

            except Exception as e:
                logger.error(f"Error processing commission {commission.id}: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Error processing commission {commission.id}: {str(e)}"))

        # Summary
        self.stdout.write(self.style.SUCCESS(f"\n✓ Commission Processing Complete:"))
        self.stdout.write(f"  Approved: {approved_count} commissions (₦{total_approved:,.2f})")
        self.stdout.write(f"  Paid: {paid_count} commissions (₦{total_paid:,.2f})")
        self.stdout.write(f"  Total: ₦{total_approved + total_paid:,.2f}")
