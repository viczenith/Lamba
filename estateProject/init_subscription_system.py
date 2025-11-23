#!/usr/bin/env python
"""
Initialize Subscription Billing System
Creates tables and establishes default subscriptions for existing companies
"""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.db import connection
from django.core.management import call_command
from estateApp.models import Company, SubscriptionPlan
from estateApp.subscription_billing_models import SubscriptionBillingModel
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

print("\n" + "="*80)
print("SUBSCRIPTION SYSTEM INITIALIZATION")
print("="*80 + "\n")

# Step 1: Create tables using Django ORM
print("[STEP 1] Creating subscription billing tables...")
try:
    from django.core.management.sql import emit_post_migrate_signal
    from django.db.backends.base.schema import BaseSchemEditor
    
    # Create the tables
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(SubscriptionBillingModel)
    
    print("✅ Tables created successfully\n")
except Exception as e:
    if "already exists" in str(e):
        print(f"ℹ️  Tables already exist\n")
    else:
        print(f"⚠️  Error creating tables: {e}\n")

# Step 2: Ensure SubscriptionPlan exists
print("[STEP 2] Ensuring subscription plans exist...")
try:
    professional_plan = SubscriptionPlan.objects.get(tier='professional')
    print(f"✅ Found plan: {professional_plan.name}\n")
except SubscriptionPlan.DoesNotExist:
    print("ℹ️  No plans found. You may need to run: python manage.py loaddata subscription_plans\n")

# Step 3: Create subscriptions for all companies
print("[STEP 3] Assigning subscriptions to companies...")
all_companies = Company.objects.all()
print(f"Found {all_companies.count()} companies\n")

created_count = 0
skipped_count = 0
error_count = 0

for company in all_companies:
    try:
        billing, created = SubscriptionBillingModel.objects.get_or_create(
            company=company,
            defaults={
                'status': 'trial',
                'payment_method': 'free_trial',
                'trial_started_at': timezone.now(),
                'trial_ends_at': timezone.now() + timedelta(days=14),
                'billing_cycle': 'monthly',
                'auto_renew': False,
                'monthly_amount': Decimal('0.00'),
                'annual_amount': Decimal('0.00'),
            }
        )
        
        if created:
            created_count += 1
            print(f"✓ Created subscription for: {company.company_name}")
            
            # Update company trial dates if needed
            if not company.trial_ends_at:
                company.trial_ends_at = timezone.now() + timedelta(days=14)
                company.subscription_status = 'trial'
                company.save()
        else:
            skipped_count += 1
            print(f"ℹ️  Already has subscription: {company.company_name}")
    
    except Exception as e:
        error_count += 1
        print(f"❌ Error for {company.company_name}: {e}")

print(f"\n" + "="*80)
print(f"RESULTS:")
print(f"  ✅ Created: {created_count}")
print(f"  ℹ️  Skipped: {skipped_count}")
print(f"  ❌ Errors: {error_count}")
print("="*80 + "\n")

sys.exit(0 if error_count == 0 else 1)
