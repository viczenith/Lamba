#!/usr/bin/env python
"""
Test script to verify client and marketer registration functionality
"""
import os
import sys
import django
from datetime import datetime

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import RequestFactory, TestCase
from estateApp.views import client_registration, marketer_registration
from estateApp.models import CustomUser

def test_client_registration():
    """Test client registration with valid data"""
    print("Testing client registration...")

    # Create a mock request
    factory = RequestFactory()
    request = factory.post('/client-register/', {
        'first_name': 'Test',
        'last_name': 'Client',
        'email': 'testclient@example.com',
        'phone': '+1234567890',
        'date_of_birth': '1990-01-01',
        'password': 'testpassword123',
        'confirm_password': 'testpassword123'
    })

    # Add AJAX header
    request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

    try:
        response = client_registration(request)
        print(f"Response status: {response.status_code}")

        if hasattr(response, 'content'):
            import json
            try:
                data = json.loads(response.content.decode('utf-8'))
                print(f"Response data: {data}")
                if data.get('success'):
                    print("✅ Client registration successful!")
                    # Check if user was created
                    user = CustomUser.objects.filter(email='testclient@example.com').first()
                    if user:
                        print(f"✅ User created: {user.full_name}, DOB: {user.date_of_birth}")
                    else:
                        print("❌ User was not created in database")
                else:
                    print(f"❌ Registration failed: {data.get('message')}")
            except json.JSONDecodeError:
                print(f"Response content: {response.content.decode('utf-8')}")
        else:
            print("Response has no content attribute")

    except Exception as e:
        print(f"❌ Error during client registration: {str(e)}")
        import traceback
        traceback.print_exc()

def test_marketer_registration():
    """Test marketer registration with valid data"""
    print("\nTesting marketer registration...")

    # Create a mock request
    factory = RequestFactory()
    request = factory.post('/marketer-register/', {
        'first_name': 'Test',
        'last_name': 'Marketer',
        'email': 'testmarketer@example.com',
        'phone': '+1234567890',
        'date_of_birth': '1985-05-15',
        'password': 'testpassword123',
        'confirm_password': 'testpassword123'
    })

    # Add AJAX header
    request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

    try:
        response = marketer_registration(request)
        print(f"Response status: {response.status_code}")

        if hasattr(response, 'content'):
            import json
            try:
                data = json.loads(response.content.decode('utf-8'))
                print(f"Response data: {data}")
                if data.get('success'):
                    print("✅ Marketer registration successful!")
                    # Check if user was created
                    user = CustomUser.objects.filter(email='testmarketer@example.com').first()
                    if user:
                        print(f"✅ User created: {user.full_name}, DOB: {user.date_of_birth}")
                    else:
                        print("❌ User was not created in database")
                else:
                    print(f"❌ Registration failed: {data.get('message')}")
            except json.JSONDecodeError:
                print(f"Response content: {response.content.decode('utf-8')}")
        else:
            print("Response has no content attribute")

    except Exception as e:
        print(f"❌ Error during marketer registration: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("Starting registration tests...")
    test_client_registration()
    test_marketer_registration()
    print("\nTest completed!")