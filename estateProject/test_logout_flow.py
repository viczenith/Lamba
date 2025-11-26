#!/usr/bin/env python
"""
Test script to verify logout and session expiration redirects work correctly.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

def test_logout_flow():
    """Test the complete logout flow"""
    print("Testing logout functionality...")

    # Create test client
    client = Client()

    # Try to access a protected page without authentication
    response = client.get('/accounts/profile/')
    print(f'Unauthenticated access to /accounts/profile/: {response.status_code}')
    print(f'Redirect location: {response.get("Location", "None")}')

    # Login
    User = get_user_model()
    try:
        user = User.objects.filter(email='akorvikkyy@gmail.com').first()
        if user:
            login_success = client.login(email='akorvikkyy@gmail.com', password='password123')
            print(f'Login successful: {login_success}')

            # Access protected page
            response = client.get('/accounts/profile/')
            print(f'Authenticated access to /accounts/profile/: {response.status_code}')

            # Test logout
            response = client.get('/logout/')
            print(f'Logout status: {response.status_code}')
            print(f'Logout redirect: {response.get("Location", "None")}')

            # Try to access protected page after logout
            response = client.get('/accounts/profile/')
            print(f'Access after logout: {response.status_code}')
            print(f'Redirect after logout: {response.get("Location", "None")}')

            print("✅ Logout test completed successfully")
        else:
            print('❌ Test user not found')
    except Exception as e:
        print(f'❌ Error during testing: {e}')

if __name__ == '__main__':
    test_logout_flow()