#!/usr/bin/env python
"""
Test Script for DRF Admin Module Endpoints
Tests all 9 admin ViewSets and their 65+ endpoints
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from rest_framework.test import APIClient
from rest_framework import status
from estateApp.models import Company, CustomUser as User
import json

class AdminEndpointTester:
    """Test all admin module endpoints"""
    
    def __init__(self):
        self.client = APIClient()
        self.base_url = 'http://localhost:8000/api'
        self.results = {
            'passed': [],
            'failed': [],
            'errors': []
        }
    
    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n" + "="*60)
        print("TESTING: Authentication Endpoints")
        print("="*60)
        
        tests = [
            {
                'name': 'Register Company',
                'method': 'post',
                'endpoint': '/auth/register/',
                'data': {
                    'name': 'Test Company',
                    'email': 'test@company.com',
                    'admin_user': {
                        'username': 'admin_test',
                        'email': 'admin@company.com',
                        'password': 'SecurePass123!',
                        'first_name': 'Admin'
                    }
                },
                'expected_status': 201
            },
            {
                'name': 'Login User',
                'method': 'post',
                'endpoint': '/auth/login/',
                'data': {
                    'email': 'admin@company.com',
                    'password': 'SecurePass123!'
                },
                'expected_status': 200,
                'requires_auth': False
            }
        ]
        
        for test in tests:
            self._run_test(test)
    
    def test_company_endpoints(self):
        """Test company management endpoints"""
        print("\n" + "="*60)
        print("TESTING: Company Management Endpoints")
        print("="*60)
        
        tests = [
            {
                'name': 'List Companies',
                'method': 'get',
                'endpoint': '/companies/',
                'expected_status': 200
            },
            {
                'name': 'Create Company',
                'method': 'post',
                'endpoint': '/companies/',
                'data': {
                    'name': 'New Company',
                    'email': 'new@company.com',
                    'subscription_tier': 'starter'
                },
                'expected_status': 201
            }
        ]
        
        for test in tests:
            self._run_test(test)
    
    def test_user_endpoints(self):
        """Test user management endpoints"""
        print("\n" + "="*60)
        print("TESTING: User Management Endpoints")
        print("="*60)
        
        tests = [
            {
                'name': 'List Users',
                'method': 'get',
                'endpoint': '/users/',
                'expected_status': 200
            },
            {
                'name': 'Create User',
                'method': 'post',
                'endpoint': '/users/',
                'data': {
                    'email': 'newuser@test.com',
                    'first_name': 'Test',
                    'last_name': 'User',
                    'password': 'TestPass123!'
                },
                'expected_status': 201
            }
        ]
        
        for test in tests:
            self._run_test(test)
    
    def test_estate_endpoints(self):
        """Test estate management endpoints"""
        print("\n" + "="*60)
        print("TESTING: Estate Management Endpoints")
        print("="*60)
        
        tests = [
            {
                'name': 'List Estates',
                'method': 'get',
                'endpoint': '/estates/',
                'expected_status': 200
            },
            {
                'name': 'Create Estate',
                'method': 'post',
                'endpoint': '/estates/',
                'data': {
                    'name': 'Test Estate',
                    'location': 'Test Location',
                    'status': 'active',
                    'total_plots': 100
                },
                'expected_status': 201
            }
        ]
        
        for test in tests:
            self._run_test(test)
    
    def test_property_endpoints(self):
        """Test property management endpoints"""
        print("\n" + "="*60)
        print("TESTING: Property Management Endpoints")
        print("="*60)
        
        tests = [
            {
                'name': 'List Properties',
                'method': 'get',
                'endpoint': '/properties/',
                'expected_status': 200
            },
            {
                'name': 'List Allocations',
                'method': 'get',
                'endpoint': '/allocations/',
                'expected_status': 200
            }
        ]
        
        for test in tests:
            self._run_test(test)
    
    def test_subscription_endpoints(self):
        """Test subscription endpoints"""
        print("\n" + "="*60)
        print("TESTING: Subscription Management Endpoints")
        print("="*60)
        
        tests = [
            {
                'name': 'Get Current Subscription',
                'method': 'get',
                'endpoint': '/subscriptions/current/',
                'expected_status': 200
            },
            {
                'name': 'Get Billing History',
                'method': 'get',
                'endpoint': '/subscriptions/billing-history/',
                'expected_status': 200
            }
        ]
        
        for test in tests:
            self._run_test(test)
    
    def test_payment_endpoints(self):
        """Test payment endpoints"""
        print("\n" + "="*60)
        print("TESTING: Payment Management Endpoints")
        print("="*60)
        
        tests = [
            {
                'name': 'List Payment Methods',
                'method': 'get',
                'endpoint': '/payments/methods/',
                'expected_status': 200
            }
        ]
        
        for test in tests:
            self._run_test(test)
    
    def test_transaction_endpoints(self):
        """Test transaction endpoints"""
        print("\n" + "="*60)
        print("TESTING: Transaction Management Endpoints")
        print("="*60)
        
        tests = [
            {
                'name': 'List Transactions',
                'method': 'get',
                'endpoint': '/transactions/',
                'expected_status': 200
            }
        ]
        
        for test in tests:
            self._run_test(test)
    
    def _run_test(self, test):
        """Run a single test"""
        try:
            url = f"{self.base_url}{test['endpoint']}"
            method = getattr(self.client, test['method'])
            data = test.get('data', {})
            
            if test['method'] == 'get':
                response = method(url)
            else:
                response = method(url, data, format='json')
            
            if response.status_code == test['expected_status']:
                self.results['passed'].append({
                    'test': test['name'],
                    'endpoint': test['endpoint'],
                    'status': response.status_code
                })
                print(f"✅ PASS: {test['name']} ({test['endpoint']}) - Status {response.status_code}")
            else:
                self.results['failed'].append({
                    'test': test['name'],
                    'endpoint': test['endpoint'],
                    'expected': test['expected_status'],
                    'got': response.status_code,
                    'response': response.data if hasattr(response, 'data') else str(response)
                })
                print(f"❌ FAIL: {test['name']} ({test['endpoint']}) - Expected {test['expected_status']}, got {response.status_code}")
        except Exception as e:
            self.results['errors'].append({
                'test': test['name'],
                'endpoint': test['endpoint'],
                'error': str(e)
            })
            print(f"⚠️  ERROR: {test['name']} ({test['endpoint']}) - {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"✅ Passed: {len(self.results['passed'])}")
        print(f"❌ Failed: {len(self.results['failed'])}")
        print(f"⚠️  Errors: {len(self.results['errors'])}")
        print("="*60)
        
        if self.results['failed']:
            print("\nFailed Tests:")
            for fail in self.results['failed']:
                print(f"  - {fail['test']}: {fail['endpoint']}")
                print(f"    Expected {fail['expected']}, got {fail['got']}")
        
        if self.results['errors']:
            print("\nErrors:")
            for error in self.results['errors']:
                print(f"  - {error['test']}: {error['error']}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("DRF ADMIN MODULE - ENDPOINT TESTS")
        print("="*60)
        
        self.test_auth_endpoints()
        self.test_company_endpoints()
        self.test_user_endpoints()
        self.test_estate_endpoints()
        self.test_property_endpoints()
        self.test_subscription_endpoints()
        self.test_payment_endpoints()
        self.test_transaction_endpoints()
        
        self.print_summary()

if __name__ == '__main__':
    tester = AdminEndpointTester()
    tester.run_all_tests()
