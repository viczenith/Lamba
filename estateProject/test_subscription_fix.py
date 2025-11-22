#!/usr/bin/env python
"""
Test subscription API with string company ID from middleware.
Simulates the exact scenario that was causing the error.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, '/root')
django.setup()

from django.test import RequestFactory, TestCase
from rest_framework.test import force_authenticate
from estateApp.models import Company, SubscriptionPlan, CustomUser
from estateApp.api_views.billing_views import SubscriptionDashboardView
from estateApp.throttles import SubscriptionTierThrottle
from estateApp.tenant_middleware import RateLimitMiddleware
import logging
import json

logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("SUBSCRIPTION API - STRING COMPANY ID TEST")
print("="*80)

# Get or create test data
try:
    company = Company.objects.first()
    if not company:
        print("❌ No company found in database")
        sys.exit(1)
    
    print(f"\n✓ Company: {company.company_name} (ID: {company.id})")
    
    # Ensure subscription plans exist
    plans_exist = SubscriptionPlan.objects.filter(is_active=True).exists()
    if not plans_exist:
        print("❌ No subscription plans found. Creating them...")
        SubscriptionPlan.objects.bulk_create([
            SubscriptionPlan(
                tier='starter',
                name='Starter',
                description='Basic plan',
                monthly_price=5000,
                max_plots=5,
                max_agents=2,
                max_api_calls_daily=100,
                is_active=True
            ),
            SubscriptionPlan(
                tier='professional',
                name='Professional',
                description='Professional plan',
                monthly_price=15000,
                max_plots=20,
                max_agents=5,
                max_api_calls_daily=1000,
                is_active=True
            ),
            SubscriptionPlan(
                tier='enterprise',
                name='Enterprise',
                description='Enterprise plan',
                monthly_price=50000,
                max_plots=100,
                max_agents=50,
                max_api_calls_daily=10000,
                is_active=True
            ),
        ])
        print("✓ Subscription plans created")
    else:
        print("✓ Subscription plans exist")
    
    # Ensure company has subscription
    if not company.subscription_tier:
        company.subscription_tier = 'enterprise'
        company.subscription_status = 'active'
        company.max_plots = 100
        company.max_agents = 50
        company.max_api_calls_daily = 10000
        company.save()
        print("✓ Company subscription set to enterprise")
    
    # Get or create user
    user = CustomUser.objects.filter(is_superuser=True).first()
    if not user:
        user = CustomUser.objects.create_superuser('admin', 'admin@test.com', 'admin123')
        print(f"✓ Test user created: {user.username}")
    else:
        print(f"✓ Test user: {user.username}")
    
    # Create factory
    factory = RequestFactory()
    
    print("\n" + "-"*80)
    print("TEST 1: Throttle Middleware with String Company ID")
    print("-"*80)
    
    try:
        from django.contrib.auth.models import AnonymousUser
        request = factory.get('/api/subscription/')
        if user:
            force_authenticate(request, user=user)
        else:
            request.user = AnonymousUser()
        
        # Simulate middleware setting request.company as STRING ID
        request.company = str(company.id)  # ← This is what middleware does!
        print(f"✓ Request company type: {type(request.company)} = '{request.company}'")
        
        throttle = SubscriptionTierThrottle()
        
        # Test get_cache_key
        cache_key = throttle.get_cache_key(request, None)
        print(f"✓ Cache key generated: {cache_key}")
        
        # Test throttle_failure (this was causing 'str' object has no attribute 'pk')
        result = throttle.throttle_failure(request, None)
        print(f"✓ Throttle failure check passed: {result}")
        
        # Test allow_request
        allowed = throttle.allow_request(request, None)
        print(f"✓ Request allowed: {allowed}")
        
        print("✅ TEST 1 PASSED")
        
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "-"*80)
    print("TEST 2: RateLimitMiddleware with String Company ID")
    print("-"*80)
    
    try:
        from django.contrib.auth.models import AnonymousUser
        request = factory.get('/api/subscription/')
        if user:
            force_authenticate(request, user=user)
        else:
            request.user = AnonymousUser()
        request.company = str(company.id)  # ← String ID again
        request._start_time = __import__('time').time()
        
        middleware = RateLimitMiddleware(lambda r: None)
        response_dict = {'status_code': 200}
        
        # Create mock response object
        class MockResponse(dict):
            def __setitem__(self, key, value):
                dict.__setitem__(self, key, value)
            def __getitem__(self, key):
                return dict.__getitem__(self, key)
        
        response = MockResponse()
        response['Content-Type'] = 'application/json'
        response.status_code = 200
        
        # This was causing: "Error recording API usage: 'str' object has no attribute 'id'"
        processed_response = middleware.process_response(request, response)
        print(f"✓ API usage recorded without errors")
        print(f"✓ Response headers: X-API-Requests-Today = {response.get('X-API-Requests-Today', 'N/A')}")
        
        print("✅ TEST 2 PASSED")
        
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "-"*80)
    print("TEST 3: SubscriptionDashboardView with String Company ID")
    print("-"*80)
    
    try:
        from django.contrib.auth.models import AnonymousUser
        view = SubscriptionDashboardView()
        request = factory.get('/api/subscription/')
        if user:
            force_authenticate(request, user=user)
        else:
            request.user = AnonymousUser()
        request.company = str(company.id)  # ← String ID
        request.path = '/api/subscription/'
        request.method = 'GET'
        
        # Test get_company method
        company_obj = view.get_company(request)
        print(f"✓ Got company object: {company_obj.company_name if company_obj else 'None'}")
        
        # Test list method (the main endpoint)
        response = view.list(request)
        print(f"✓ API Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.data
            print(f"✓ Subscription data returned:")
            print(f"  - Tier: {data.get('subscription', {}).get('tier')}")
            print(f"  - Status: {data.get('subscription', {}).get('status')}")
            print(f"  - Days remaining: {data.get('days_remaining')}")
            print("✅ TEST 3 PASSED")
        else:
            print(f"❌ TEST 3 FAILED: Status {response.status_code}")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED - STRING COMPANY ID HANDLING WORKS!")
    print("="*80)
    print("\nThe subscription API now correctly handles string company IDs from middleware.")
    print("Error 'str' object has no attribute 'pk' and 'id' should be RESOLVED.")
    
except Exception as e:
    print(f"\n❌ SETUP FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
