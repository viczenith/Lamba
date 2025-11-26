#!/usr/bin/env python
"""
Test script to verify logout functionality and session expiration.
"""
import os
import sys
import django
from django.test import Client
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

User = get_user_model()

def test_logout_redirect():
    """Test that logout redirects to login page"""
    client = Client()

    # Create a test user if needed
    try:
        user = User.objects.filter(email='test@example.com').first()
        if not user:
            user = User.objects.create_user(
                email='test@example.com',
                full_name='Test User',
                phone='1234567890',
                password='testpass123'
            )
            print("Created test user")
    except Exception as e:
        print(f"Could not create user: {e}")
        return

    # Login
    login_response = client.post('/login/', {
        'username': 'test@example.com',
        'password': 'testpass123'
    })

    print(f"Login status: {login_response.status_code}")
    print(f"Login redirect: {login_response.get('Location', 'No redirect')}")

    # Logout
    logout_response = client.get('/logout/')

    print(f"Logout status: {logout_response.status_code}")
    print(f"Logout redirect: {logout_response.get('Location', 'No redirect')}")

    # Check if user is actually logged out
    profile_response = client.get('/accounts/profile/')
    print(f"Profile access after logout: {profile_response.status_code}")
    
    if profile_response.status_code == 302 and 'login' in profile_response.get('Location', ''):
        print("✅ User successfully logged out")
    else:
        print("❌ User may still be logged in")

if __name__ == '__main__':
    test_logout_redirect()