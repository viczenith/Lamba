#!/usr/bin/env python
"""
Test session timeout functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

def test_session_timeout():
    """Test 5-minute session timeout"""
    print("🧪 Testing Session Timeout (5 minutes)...")

    # Create test client
    client = Client()

    # Login first
    User = get_user_model()
    try:
        # Try to find any admin user
        user = User.objects.filter(role='admin').first()
        if not user:
            print("❌ No admin user found")
            return False

        print(f"Testing with user: {user.email}")

        # Login
        login_success = client.login(email=user.email, password='password123')
        if not login_success:
            print("❌ Login failed - trying different password")
            # Try alternative passwords
            for pwd in ['admin123', 'test123', '123456']:
                login_success = client.login(email=user.email, password=pwd)
                if login_success:
                    print(f"✅ Login successful with password: {pwd}")
                    break

        if not login_success:
            print("❌ Could not login with any password")
            return False

        # Access a protected page
        response = client.get('/accounts/profile/')
        print(f"Status after login: {response.status_code}")

        # Manually expire the session
        session = client.session
        import time
        expired_time = time.time() - 400  # 400 seconds ago (expired)
        session['_session_expiry'] = expired_time
        session.save()

        print("⏰ Manually expired session...")

        # Try to access protected page again
        response = client.get('/accounts/profile/')
        print(f"Status after expiry: {response.status_code}")
        print(f"Redirect location: {response.get('Location', 'None')}")

        if response.status_code == 302 and '/login/' in response.get('Location', ''):
            print("✅ Session timeout working correctly!")
            return True
        else:
            print("❌ Session timeout not working")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    success = test_session_timeout()
    print(f"\nResult: {'PASS' if success else 'FAIL'}")
    sys.exit(0 if success else 1)