#!/usr/bin/env python
"""
Django test for client and marketer registration functionality
"""
import os
import sys
import django
from datetime import datetime

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from estateApp.models import CustomUser

class RegistrationTestCase(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    @override_settings(CSRF_COOKIE_SECURE=False, CSRF_COOKIE_HTTPONLY=False)
    def test_client_registration_ajax(self):
        """Test client registration via AJAX"""
        print("Testing client registration via AJAX...")

        # Get the CSRF token first
        response = self.client.get(reverse('login'))
        csrf_token = response.cookies.get('csrftoken')  # Get from cookies
        if not csrf_token:
            # Try to extract from context if available
            csrf_token = response.context.get('csrf_token') if response.context else None

        # If still no token, get it from the response content
        if not csrf_token and hasattr(response, 'content'):
            import re
            match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.content.decode())
            if match:
                csrf_token = match.group(1)

        self.assertIsNotNone(csrf_token, "CSRF token should be available")

        response = self.client.post('/client/register/', {
            'csrfmiddlewaretoken': csrf_token,
            'first_name': 'Test',
            'last_name': 'Client',
            'email': 'testclient@example.com',
            'phone': '+1234567890',
            'date_of_birth': '1990-01-01',
            'password': 'testpassword123',
            'confirm_password': 'testpassword123'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.content.decode('utf-8')}")

        # Check if user was created
        user = CustomUser.objects.filter(email='testclient@example.com').first()
        if user:
            print(f"✅ User created: {user.full_name}, DOB: {user.date_of_birth}")
        else:
            print("❌ User was not created in database")

        self.assertEqual(response.status_code, 200)
        self.assertIn('success', response.json())

    @override_settings(CSRF_COOKIE_SECURE=False, CSRF_COOKIE_HTTPONLY=False)
    def test_marketer_registration_ajax(self):
        """Test marketer registration via AJAX"""
        print("\nTesting marketer registration via AJAX...")

        # Get the CSRF token first
        response = self.client.get(reverse('login'))
        csrf_token = response.cookies.get('csrftoken')  # Get from cookies
        if not csrf_token:
            # Try to extract from context if available
            csrf_token = response.context.get('csrf_token') if response.context else None

        # If still no token, get it from the response content
        if not csrf_token and hasattr(response, 'content'):
            import re
            match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.content.decode())
            if match:
                csrf_token = match.group(1)

        self.assertIsNotNone(csrf_token, "CSRF token should be available")

        response = self.client.post('/marketer/register/', {
            'csrfmiddlewaretoken': csrf_token,
            'first_name': 'Test',
            'last_name': 'Marketer',
            'email': 'testmarketer@example.com',
            'phone': '+1234567890',
            'date_of_birth': '1985-05-15',
            'password': 'testpassword123',
            'confirm_password': 'testpassword123'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.content.decode('utf-8')}")

        # Check if user was created
        user = CustomUser.objects.filter(email='testmarketer@example.com').first()
        if user:
            print(f"✅ User created: {user.full_name}, DOB: {user.date_of_birth}")
        else:
            print("❌ User was not created in database")

        self.assertEqual(response.status_code, 200)
        self.assertIn('success', response.json())

if __name__ == '__main__':
    import unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(RegistrationTestCase)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)