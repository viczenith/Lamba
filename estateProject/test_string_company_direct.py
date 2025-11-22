#!/usr/bin/env python
"""
Direct test of fixes for string company ID handling.
Tests the exact code paths that were causing errors.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company, SubscriptionPlan
from estateApp.throttles import SubscriptionTierThrottle

print("\n" + "="*80)
print("DIRECT TEST: String Company ID Handling in Throttles")
print("="*80)

try:
    # Get company
    company = Company.objects.first()
    if not company:
        print("❌ No company found")
        sys.exit(1)
    
    print(f"\n✓ Company: {company.company_name} (ID: {company.id})")
    print(f"✓ Current tier: {company.subscription_tier}")
    print(f"✓ Max API calls daily: {company.max_api_calls_daily}")
    
    # Ensure subscription plans exist
    if not SubscriptionPlan.objects.exists():
        print("\n⚠ Creating subscription plans...")
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
        print("✓ Plans created")
    
    print("\n" + "-"*80)
    print("TEST 1: SubscriptionTierThrottle.throttle_failure() with string ID")
    print("-"*80)
    
    # Create mock request with STRING company ID (like middleware does)
    class MockRequest:
        def __init__(self):
            self.user = type('User', (), {'is_authenticated': True})()
            self.company = str(company.id)  # ← STRING ID, not object!
            self.META = {'REMOTE_ADDR': '127.0.0.1'}
    
    request = MockRequest()
    print(f"✓ Request.company type: {type(request.company)} = '{request.company}'")
    
    throttle = SubscriptionTierThrottle()
    
    # This was causing: 'str' object has no attribute 'subscription_tier'
    try:
        result = throttle.throttle_failure(request, None)
        print(f"✓ throttle_failure() executed successfully: {result}")
        print("✅ TEST 1 PASSED - No 'str' object attribute error!")
    except AttributeError as e:
        if "'str' object has no attribute" in str(e):
            print(f"❌ TEST 1 FAILED - Still getting attribute error: {e}")
            sys.exit(1)
        raise
    
    print("\n" + "-"*80)
    print("TEST 2: SubscriptionTierThrottle.get_rate_limit_info() with string ID")
    print("-"*80)
    
    try:
        rate_info = throttle.get_rate_limit_info(request)
        print(f"✓ Rate limit info retrieved:")
        print(f"  - Limit: {rate_info.get('limit')}")
        print(f"  - Remaining: {rate_info.get('remaining')}")
        print("✅ TEST 2 PASSED - No 'str' object attribute error!")
    except AttributeError as e:
        if "'str' object has no attribute" in str(e):
            print(f"❌ TEST 2 FAILED - Still getting attribute error: {e}")
            sys.exit(1)
        raise
    
    print("\n" + "-"*80)
    print("TEST 3: RateLimitMiddleware with string company ID")
    print("-"*80)
    
    from estateApp.tenant_middleware import RateLimitMiddleware
    
    class MockResponse(dict):
        def __init__(self):
            super().__init__()
            self.status_code = 200
        
        def __setitem__(self, key, value):
            dict.__setitem__(self, key, value)
        
        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                return None
    
    request.path = '/api/subscription/'
    request.method = 'GET'
    request._start_time = __import__('time').time()
    
    middleware = RateLimitMiddleware(lambda r: None)
    response = MockResponse()
    
    # This was causing: "Error recording API usage: 'str' object has no attribute 'id'"
    try:
        processed_response = middleware.process_response(request, response)
        print(f"✓ RateLimitMiddleware.process_response() executed successfully")
        print(f"✓ Response header X-API-Requests-Today: {response.get('X-API-Requests-Today')}")
        print("✅ TEST 3 PASSED - No 'str' object attribute error!")
    except AttributeError as e:
        if "'str' object has no attribute" in str(e):
            print(f"❌ TEST 3 FAILED - Still getting attribute error: {e}")
            sys.exit(1)
        raise
    
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED!")
    print("="*80)
    print("\nSummary:")
    print("  ✓ String company IDs handled in throttle_failure()")
    print("  ✓ String company IDs handled in get_rate_limit_info()")
    print("  ✓ String company IDs handled in RateLimitMiddleware")
    print("\nThe subscription API errors should now be RESOLVED.")
    print("Errors fixed:")
    print("  • 'str' object has no attribute 'pk'")
    print("  • 'str' object has no attribute 'id'")
    print("  • Error recording API usage")
    
except Exception as e:
    print(f"\n❌ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
