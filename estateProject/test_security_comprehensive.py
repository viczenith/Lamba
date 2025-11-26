#!/usr/bin/env python
"""
Comprehensive test for session timeout and tenancy isolation security.
"""
import os
import sys
import django
import time
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from estateApp.middleware import SessionExpirationMiddleware, TenantIsolationMiddleware
from superAdmin.enhanced_middleware import EnhancedTenantIsolationMiddleware

def test_session_timeout():
    """Test 5-minute session timeout functionality"""
    print("🧪 Testing Session Timeout (5 minutes)...")

    # Create test client
    client = Client()

    # Login first
    User = get_user_model()
    try:
        user = User.objects.filter(email='akorvikkyy@gmail.com').first()
        if not user:
            print("❌ No test user found")
            return False

        # Login
        login_success = client.login(email='akorvikkyy@gmail.com', password='password123')
        if not login_success:
            print("❌ Login failed")
            return False

        print("✅ User logged in successfully")

        # Access a protected page
        response = client.get('/accounts/profile/')
        if response.status_code != 200:
            print(f"❌ Unexpected response after login: {response.status_code}")
            return False

        print("✅ Protected page accessible after login")

        # Simulate session expiration by manually setting expiry time
        session = client.session
        expired_time = (datetime.now() - timedelta(minutes=6)).timestamp()  # 6 minutes ago
        session['_session_expiry'] = expired_time
        session.save()

        print("⏰ Simulating 5+ minute inactivity...")

        # Try to access protected page again - should redirect to login
        response = client.get('/accounts/profile/')
        if response.status_code == 302 and '/login/' in response.get('Location', ''):
            print("✅ Session expired correctly - redirected to login")
            return True
        else:
            print(f"❌ Session did not expire properly. Status: {response.status_code}, Location: {response.get('Location')}")
            return False

    except Exception as e:
        print(f"❌ Error during session timeout test: {e}")
        return False

def test_tenancy_isolation():
    """Test tenancy isolation security"""
    print("\n🛡️  Testing Tenancy Isolation Security...")

    # Test middleware isolation
    factory = RequestFactory()

    # Create mock users from different companies
    User = get_user_model()
    try:
        users = User.objects.filter(role='admin')[:2]  # Get 2 admin users
        if len(users) < 2:
            print("❌ Need at least 2 admin users for tenancy test")
            return False

        user1, user2 = users[0], users[1]

        # Test that user1 cannot access user2's company data
        request = factory.get('/admin_dashboard/')
        request.user = user1

        # Process through tenant isolation middleware
        middleware = TenantIsolationMiddleware()
        result = middleware.process_request(request)

        if result is None:  # Should proceed normally
            company1 = getattr(request, 'company', None)
            print(f"✅ User {user1.email} assigned to company: {company1.company_name if company1 else 'None'}")

            # Now test user2
            request2 = factory.get('/admin_dashboard/')
            request2.user = user2
            result2 = middleware.process_request(request2)

            if result2 is None:
                company2 = getattr(request2, 'company', None)
                print(f"✅ User {user2.email} assigned to company: {company2.company_name if company2 else 'None'}")

                # Verify they are in different companies
                if company1 and company2 and company1.id != company2.id:
                    print("✅ Tenancy isolation working - users in different companies")
                    return True
                else:
                    print("❌ Tenancy isolation failed - users in same company or no company assigned")
                    return False
            else:
                print("❌ User2 request blocked unexpectedly")
                return False
        else:
            print("❌ User1 request blocked unexpectedly")
            return False

    except Exception as e:
        print(f"❌ Error during tenancy isolation test: {e}")
        return False

def test_enhanced_security_headers():
    """Test security headers middleware"""
    print("\n🔒 Testing Security Headers...")

    factory = RequestFactory()
    request = factory.get('/')
    request.user = type('MockUser', (), {'is_authenticated': True})()

    from superAdmin.enhanced_middleware import SecurityHeadersMiddleware
    middleware = SecurityHeadersMiddleware()

    # Create a mock response
    class MockResponse:
        def __init__(self):
            self._headers = {}

        def __setitem__(self, key, value):
            self._headers[key] = value

        def __getitem__(self, key):
            return self._headers.get(key)

        def get(self, key, default=None):
            return self._headers.get(key, default)

    response = MockResponse()
    result = middleware.process_response(request, response)

    # Check for security headers
    security_headers = [
        'X-Frame-Options',
        'X-Content-Type-Options',
        'X-XSS-Protection',
        'Content-Security-Policy',
        'Referrer-Policy',
        'Feature-Policy'
    ]

    missing_headers = []
    for header in security_headers:
        if header not in response._headers:
            missing_headers.append(header)

    if not missing_headers:
        print("✅ All security headers present")
        return True
    else:
        print(f"❌ Missing security headers: {missing_headers}")
        return False

def main():
    """Run all security tests"""
    print("🚀 Starting Comprehensive Security Test Suite\n")

    results = []

    # Test session timeout
    session_test = test_session_timeout()
    results.append(("Session Timeout (5min)", session_test))

    # Test tenancy isolation
    tenancy_test = test_tenancy_isolation()
    results.append(("Tenancy Isolation", tenancy_test))

    # Test security headers
    headers_test = test_enhanced_security_headers()
    results.append(("Security Headers", headers_test))

    # Summary
    print("\n" + "="*50)
    print("📊 SECURITY TEST RESULTS")
    print("="*50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n🎯 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All security measures are working correctly!")
        return True
    else:
        print("⚠️  Some security issues detected. Please review and fix.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)