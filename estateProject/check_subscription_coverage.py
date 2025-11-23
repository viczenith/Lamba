#!/usr/bin/env python
"""
Diagnostic script to check subscription plan coverage
Identifies companies without subscription billing records
"""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company, SubscriptionPlan
from estateApp.subscription_billing_models import SubscriptionBillingModel
from django.utils import timezone
from datetime import timedelta

print("\n" + "="*80)
print("SUBSCRIPTION COVERAGE DIAGNOSTIC")
print("="*80 + "\n")

# Get all companies
all_companies = Company.objects.all()
print(f"📊 Total Companies: {all_companies.count()}")

# Find companies without subscription plans
companies_without_subscription = []
companies_with_subscription = []
companies_with_issues = []

for company in all_companies:
    try:
        billing = SubscriptionBillingModel.objects.get(company=company)
        companies_with_subscription.append((company, billing))
    except SubscriptionBillingModel.DoesNotExist:
        companies_without_subscription.append(company)

print(f"\n✅ Companies WITH Subscription Plans: {len(companies_with_subscription)}")
print(f"❌ Companies WITHOUT Subscription Plans: {len(companies_without_subscription)}")

# Display companies without subscription
if companies_without_subscription:
    print("\n" + "-"*80)
    print("COMPANIES NEEDING SUBSCRIPTION PLANS:")
    print("-"*80)
    for i, company in enumerate(companies_without_subscription, 1):
        print(f"\n{i}. {company.company_name}")
        print(f"   ID: {company.id}")
        print(f"   Tier: {company.subscription_tier}")
        print(f"   Status: {company.subscription_status}")
        print(f"   Trial Ends: {company.trial_ends_at}")
        print(f"   Created: {company.created_at if hasattr(company, 'created_at') else 'N/A'}")

# Display detailed info for companies with subscriptions
if companies_with_subscription:
    print("\n" + "-"*80)
    print("COMPANIES WITH SUBSCRIPTION PLANS:")
    print("-"*80)
    for i, (company, billing) in enumerate(companies_with_subscription, 1):
        plan_name = billing.current_plan.name if billing.current_plan else "NO PLAN"
        print(f"\n{i}. {company.company_name}")
        print(f"   Tier: {company.subscription_tier}")
        print(f"   Billing Status: {billing.status}")
        print(f"   Plan: {plan_name}")
        print(f"   Trial Ends: {billing.trial_ends_at}")
        print(f"   Subscription Ends: {billing.subscription_ends_at}")
        
        # Check for issues
        if not billing.current_plan and billing.status != 'trial':
            companies_with_issues.append((company, "Has billing record but no plan assigned"))

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"✅ Companies Ready: {len(companies_with_subscription)}")
print(f"❌ Companies Needing Fixes: {len(companies_without_subscription)}")
print(f"⚠️  Companies With Issues: {len(companies_with_issues)}")

# Available plans
print("\n" + "-"*80)
print("AVAILABLE SUBSCRIPTION PLANS:")
print("-"*80)
plans = SubscriptionPlan.objects.all()
for plan in plans:
    print(f"✓ {plan.name} (Tier: {plan.tier})")

print("\n" + "="*80 + "\n")

# Exit code
if companies_without_subscription:
    sys.exit(1)
else:
    sys.exit(0)
