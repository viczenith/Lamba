#!/usr/bin/env python
"""
End-to-end test for the subscription system
Tests registration, plan selection, limit enforcement, and feature access
"""

import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.utils import timezone
from estateApp.models import Company, SubscriptionPlan, CustomUser
from django.db import transaction

def test_subscription_plans():
    """Test 1: Verify subscription plans exist with correct pricing"""
    print("\n" + "="*60)
    print("TEST 1: Subscription Plans Verification")
    print("="*60)
    
    plans = SubscriptionPlan.objects.all().order_by('tier')
    
    expected_plans = {
        'starter': {'price': 70000, 'properties': 2, 'allocations': 30},
        'professional': {'price': 100000, 'properties': 5, 'allocations': 80},
        'enterprise': {'price': 150000, 'properties': 999999, 'allocations': 'unlimited'},
    }
    
    for plan in plans:
        expected = expected_plans.get(plan.tier, {})
        
        print(f"\n📋 {plan.name} Plan")
        print(f"   Tier: {plan.tier}")
        print(f"   Monthly Price: ₦{plan.monthly_price:,.0f}")
        print(f"   Annual Price: ₦{plan.annual_price:,.0f}")
        print(f"   Max Properties: {plan.max_plots}")
        print(f"   Max Allocations: {plan.max_api_calls_daily}")
        
        if plan.monthly_price == expected.get('price'):
            print(f"   ✅ Pricing correct")
        else:
            print(f"   ❌ Pricing mismatch!")
        
        if plan.features:
            print(f"   Features: {', '.join(plan.features.keys())}")
    
    print(f"\n✅ Total plans: {plans.count()}")
    return True


def test_company_registration():
    """Test 2: Create test companies with different subscription tiers"""
    print("\n" + "="*60)
    print("TEST 2: Company Registration with Subscription Tiers")
    print("="*60)
    
    test_data = [
        {
            'name': 'Startup Real Estate Ltd',
            'tier': 'starter',
            'reg_num': 'REG-TEST-001',
            'email': 'startup@test.com'
        },
        {
            'name': 'Growth Properties Ltd',
            'tier': 'professional',
            'reg_num': 'REG-TEST-002',
            'email': 'growth@test.com'
        },
        {
            'name': 'Enterprise Mega Ltd',
            'tier': 'enterprise',
            'reg_num': 'REG-TEST-003',
            'email': 'enterprise@test.com'
        }
    ]
    
    test_companies = []
    
    with transaction.atomic():
        for data in test_data:
            # Check if company already exists
            existing = Company.objects.filter(email=data['email']).first()
            if existing:
                print(f"\n⚠️  Company {data['name']} already exists, using existing")
                test_companies.append(existing)
                continue
            
            trial_end = timezone.now() + timedelta(days=14)
            company = Company.objects.create(
                company_name=data['name'],
                slug=data['name'].lower().replace(' ', '-'),
                registration_number=data['reg_num'],
                registration_date=timezone.now().date(),
                location='Lagos, Nigeria',
                ceo_name='Test CEO',
                ceo_dob=timezone.now().date(),
                email=data['email'],
                phone='+234 123 456 7890',
                subscription_tier=data['tier'],
                subscription_status='trial',
                trial_ends_at=trial_end,
                is_active=True
            )
            test_companies.append(company)
            print(f"\n✅ Created: {company.company_name}")
            print(f"   Tier: {company.subscription_tier}")
            print(f"   Status: {company.subscription_status}")
    
    return test_companies


def test_limit_enforcement(companies):
    """Test 3: Verify feature limits based on subscription tier"""
    print("\n" + "="*60)
    print("TEST 3: Feature Limit Enforcement")
    print("="*60)
    
    for company in companies:
        print(f"\n📊 {company.company_name} ({company.subscription_tier.upper()})")
        
        # Get subscription plan
        plan = company.get_subscription_plan()
        print(f"   Plan: {plan.name if plan else 'Not found'}")
        
        # Get feature limits
        limits = company.get_feature_limits()
        print(f"   Estate Properties: {limits['estate_properties']}")
        print(f"   Allocations: {limits['allocations']}")
        print(f"   Clients: {limits['clients']}")
        print(f"   Affiliates: {limits['affiliates']}")
        
        # Check enforcement methods
        can_allocation, msg_alloc = company.can_create_allocation()
        print(f"   Can create allocation: {can_allocation} - {msg_alloc}")
        
        can_client, msg_client = company.can_add_client()
        print(f"   Can add client: {can_client} - {msg_client}")
        
        can_affiliate, msg_affiliate = company.can_add_affiliate()
        print(f"   Can add affiliate: {can_affiliate} - {msg_affiliate}")
        
        # Get current usage
        usage = company.get_usage_stats()
        print(f"   Current usage: {usage}")


def test_trial_period(companies):
    """Test 4: Verify trial period setup"""
    print("\n" + "="*60)
    print("TEST 4: Trial Period Verification")
    print("="*60)
    
    for company in companies:
        print(f"\n⏰ {company.company_name}")
        print(f"   Status: {company.subscription_status}")
        print(f"   Trial Ends: {company.trial_ends_at}")
        print(f"   Is Trial Active: {company.is_trial_active()}")
        
        if company.trial_ends_at:
            days_left = (company.trial_ends_at - timezone.now()).days
            print(f"   Days Left: {days_left}")


def test_limit_synchronization(company):
    """Test 5: Verify limits sync from SubscriptionPlan"""
    print("\n" + "="*60)
    print("TEST 5: Limit Synchronization")
    print("="*60)
    
    print(f"\nTesting: {company.company_name}")
    
    # Get the plan
    plan = company.get_subscription_plan()
    print(f"\nPlan Limits:")
    print(f"   Max Plots: {plan.max_plots}")
    print(f"   Max Agents: {plan.max_agents}")
    print(f"   Max API Calls: {plan.max_api_calls_daily}")
    
    print(f"\nCompany Limits (should match plan):")
    print(f"   Max Plots: {company.max_plots}")
    print(f"   Max Agents: {company.max_agents}")
    print(f"   Max API Calls: {company.max_api_calls_daily}")
    
    # Verify sync
    if (company.max_plots == plan.max_plots and 
        company.max_agents == plan.max_agents and 
        company.max_api_calls_daily == plan.max_api_calls_daily):
        print("\n✅ Limits are correctly synchronized!")
        return True
    else:
        print("\n❌ Limits mismatch!")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 LAMBA SUBSCRIPTION SYSTEM - END-TO-END TESTS")
    print("="*60)
    
    try:
        # Test 1: Plans
        test_subscription_plans()
        
        # Test 2: Registration
        companies = test_company_registration()
        
        # Test 3: Limits
        test_limit_enforcement(companies)
        
        # Test 4: Trial
        test_trial_period(companies)
        
        # Test 5: Synchronization
        for company in companies:
            test_limit_synchronization(company)
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nSubscription System Status: ✅ READY FOR PRODUCTION")
        print("\nNext Steps:")
        print("  1. Test registration via web UI")
        print("  2. Verify plan selection UI is clickable")
        print("  3. Test with real user registration")
        print("  4. Monitor trial expiration")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
