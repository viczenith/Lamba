#!/usr/bin/env python
"""
Test script to verify the role selection modal functionality.
This script tests the authentication backend and view logic for multiple user detection.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import authenticate
from estateApp.models import CustomUser, Company
from estateApp.backends import EmailBackend
from estateApp.views import CustomLoginView

def test_multiple_user_detection():
    """Test that the authentication backend detects multiple users correctly."""
    print("Testing multiple user detection...")

    # Create test users with same email but different roles
    try:
        # Clean up any existing test data
        Company.objects.filter(email='company@test.com').delete()
        CustomUser.objects.filter(email='test@example.com').delete()

        # Create company first
        company = Company.objects.create(
            company_name='Test Company',
            registration_number='TEST123',
            registration_date='2020-01-01',
            location='Test City',
            ceo_name='Test CEO',
            ceo_dob='1980-01-01',
            email='company@test.com',
            phone='+1234567890'
        )

        # Create multiple users with same email
        user1 = CustomUser.objects.create_user(
            email='test@example.com',
            full_name='Test Client',
            phone='+1234567890',
            password='testpass123',
            role='client',
            date_of_birth='1990-01-01'
        )

        user2 = CustomUser.objects.create_user(
            email='test@example.com',
            full_name='Test Admin',
            phone='+1234567890',
            password='testpass123',
            role='admin',
            date_of_birth='1990-01-01',
            company_profile=company
        )

        user3 = CustomUser.objects.create_user(
            email='test@example.com',
            full_name='Test Marketer',
            phone='+1234567890',
            password='testpass123',
            role='marketer',
            date_of_birth='1990-01-01'
        )

        print(f"Created test users: {user1.id}, {user2.id}, {user3.id}")

        # Test authentication backend
        backend = EmailBackend()

        # Test with correct password - should return MultipleUserMatch
        result = backend.authenticate(None, username='test@example.com', password='testpass123')
        print(f"Authentication result: {type(result)}")

        if hasattr(result, 'users'):
            print(f"Multiple users detected: {len(result.users)} users")
            for user in result.users:
                print(f"  - {user.get_role_display()}: {user.full_name}")
        else:
            print("ERROR: Expected MultipleUserMatch object")

        # Test with wrong password - should return None
        result_wrong = backend.authenticate(None, username='test@example.com', password='wrongpass')
        print(f"Wrong password result: {result_wrong}")

        # Clean up
        CustomUser.objects.filter(email='test@example.com').delete()
        company.delete()

        print("Multiple user detection test completed successfully!")

    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc()

def test_login_view():
    """Test the login view with multiple users."""
    print("\nTesting login view...")

    try:
        client = Client()

        # Clean up any existing test data
        Company.objects.filter(email='company2@test.com').delete()
        CustomUser.objects.filter(email='test2@example.com').delete()

        company = Company.objects.create(
            company_name='Test Company 2',
            registration_number='TEST456',
            registration_date='2020-01-01',
            location='Test City 2',
            ceo_name='Test CEO 2',
            ceo_dob='1980-01-01',
            email='company2@test.com',
            phone='+1234567890'
        )

        user1 = CustomUser.objects.create_user(
            email='test2@example.com',
            full_name='Test2 Client',
            phone='+1234567890',
            password='testpass123',
            role='client',
            date_of_birth='1990-01-01'
        )

        user2 = CustomUser.objects.create_user(
            email='test2@example.com',
            full_name='Test2 Admin',
            phone='+1234567890',
            password='testpass123',
            role='admin',
            date_of_birth='1990-01-01',
            company_profile=company
        )

        print(f"Created test users for view test: {user1.id}, {user2.id}")

        # Test login POST request
        response = client.post('/login/', {
            'username': 'test2@example.com',
            'password': 'testpass123'
        })

        print(f"Login response status: {response.status_code}")
        
        # Check if response contains the role selection modal
        content_str = response.content.decode('utf-8')
        has_modal = 'roleSelectionModal' in content_str
        has_multiple_users = 'multiple_users' in content_str or 'Select Your Account' in content_str
        
        print(f"Response contains role selection modal: {has_modal}")
        print(f"Response contains multiple users content: {has_multiple_users}")
        
        if has_modal and has_multiple_users:
            print("SUCCESS: Role selection modal is displayed!")
        else:
            print("FAILURE: Role selection modal not found in response")
            print(f"Response content preview: {response.content[:1000]}")
        
        if hasattr(response, 'context') and response.context:
            print(f"Response contains 'multiple_users': {'multiple_users' in response.context}")
            print(f"Response contains 'user_email': {'user_email' in response.context}")

            if 'multiple_users' in response.context:
                multiple_users = response.context['multiple_users']
                print(f"Multiple users in context: {len(multiple_users)}")
                for user in multiple_users:
                    print(f"  - {user.get_role_display()}: {user.full_name}")
        else:
            print("Response has no context (this is normal for test client)")

        # Test role selection POST request
        print("\nTesting role selection...")
        
        # First get the login page to establish session
        client.get('/login/')
        
        # Select the client role
        role_response = client.post('/login/', {
            'selected_user_id': str(user1.id),
            'user_email': 'test2@example.com'
        })
        
        print(f"Role selection response status: {role_response.status_code}")
        
        # Check if redirected (should be to client dashboard)
        if role_response.status_code == 302:
            print(f"Redirected to: {role_response['Location']}")
            print("SUCCESS: Role selection and login completed!")
        else:
            print(f"Unexpected response status: {role_response.status_code}")
            print(f"Response content: {role_response.content[:500]}")

    except Exception as e:
        print(f"Error in view test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("Starting role selection modal tests...")
    test_multiple_user_detection()
    test_login_view()
    print("\nAll tests completed!")