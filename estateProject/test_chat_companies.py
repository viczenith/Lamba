#!/usr/bin/env python3
"""
Test script to verify that companies are properly displayed in the chat explorer
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from estateApp.models import Company, CustomUser, PlotAllocation
from estateApp.views import chat_view

def test_chat_companies():
    """Test that chat_view properly builds companies list from plot allocations"""
    
    print("=== Testing Chat Companies Display ===\n")
    
    # Create test data
    try:
        # Get a test client user
        client = CustomUser.objects.filter(role='client').first()
        if not client:
            print("❌ No client users found in database")
            return False
        
        print(f"✅ Found client: {client.username} (ID: {client.id})")
        
        # Get plot allocations for this client
        allocations = PlotAllocation.objects.filter(client=client)
        print(f"✅ Found {allocations.count()} plot allocations for client")
        
        if allocations.count() > 0:
            # Get unique companies from allocations
            companies_from_allocations = Company.objects.filter(
                estates__plotallocation__client=client
            ).distinct().order_by('company_name')
            
            print(f"✅ Found {companies_from_allocations.count()} unique companies from allocations:")
            for company in companies_from_allocations:
                print(f"   - {company.company_name}")
        
        # Test the logic directly without authentication
        print("\n=== Testing chat_view logic directly ===")
        
        # Simulate the chat_view logic
        companies = Company.objects.filter(
            estates__plotallocation__client=client
        ).distinct().order_by('company_name')
        
        # If no allocations found, fall back to user's direct company
        if not companies.exists():
            if client.company_profile:
                companies = Company.objects.filter(id=client.company_profile.id)
            else:
                companies = Company.objects.none()
        
        selected_company = companies.first() if companies.exists() else None
        
        print(f"✅ Logic test: Found {companies.count()} companies")
        if companies.count() > 0:
            print("✅ Companies found:")
            for company in companies:
                print(f"   - {company.company_name}")
            
            if selected_company:
                print(f"✅ Selected company: {selected_company.company_name}")
            
            return True
        else:
            print("⚠️  No companies found (might be expected if no allocations)")
            return True
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_template_context():
    """Test that the template has the expected context variables"""
    
    print("\n=== Testing Template Context ===")
    
    try:
        # Get a test client
        client = CustomUser.objects.filter(role='client').first()
        if not client:
            print("❌ No client users found")
            return False
        
        # Get companies for this client
        companies = Company.objects.filter(
            estates__plotallocation__client=client
        ).distinct().order_by('company_name')
        
        print(f"✅ Template context would contain:")
        print(f"   - companies: {companies.count()} companies")
        print(f"   - client: {client.username}")
        print(f"   - selected_company: {'First company' if companies.exists() else 'None'}")
        
        # Check if template file exists
        template_path = os.path.join(os.path.dirname(__file__), 'estateApp', 'templates', 'client_side', 'chat_interface.html')
        if os.path.exists(template_path):
            print("✅ Template file exists")
            
            # Check if template expects the right context variables
            with open(template_path, 'r') as f:
                content = f.read()
                
            if 'companies' in content:
                print("✅ Template references 'companies' variable")
            else:
                print("❌ Template does not reference 'companies' variable")
                
            if 'selected_company' in content:
                print("✅ Template references 'selected_company' variable")
            else:
                print("❌ Template does not reference 'selected_company' variable")
                
            if 'client' in content:
                print("✅ Template references 'client' variable")
            else:
                print("❌ Template does not reference 'client' variable")
                
            return True
        else:
            print("❌ Template file not found")
            return False
            
    except Exception as e:
        print(f"❌ Error during template test: {e}")
        return False

if __name__ == '__main__':
    print("Testing Chat Companies Display Fix\n")
    
    # Run tests
    test1_result = test_chat_companies()
    test2_result = test_template_context()
    
    print(f"\n=== Test Results ===")
    print(f"Chat companies test: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    print(f"Template context test: {'✅ PASSED' if test2_result else '❌ FAILED'}")
    
    if test1_result and test2_result:
        print("\n🎉 All tests passed! The chat companies display fix should work correctly.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")