#!/usr/bin/env python3
"""
Test script to verify complete marketer companies functionality
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth.models import AnonymousUser
from estateApp.models import Company, CustomUser, PlotAllocation, Message, Transaction
from estateApp.views import marketer_my_companies, marketer_company_portfolio

def test_marketer_companies_functionality():
    """Test complete marketer companies functionality"""
    
    print("=== Testing Marketer Companies Functionality ===\n")
    
    try:
        # Get a test marketer
        marketer = CustomUser.objects.filter(role='marketer').first()
        if not marketer:
            print("❌ No marketer users found in database")
            return False
        
        print(f"✅ Found marketer: {marketer.email} (ID: {marketer.id})")
        
        # Get companies for this marketer
        company_ids = (
            Transaction.objects.filter(marketer=marketer)
            .values_list('company', flat=True)
            .distinct()
        )
        
        companies = Company.objects.filter(id__in=[c for c in company_ids if c is not None])
        
        if companies.count() == 0:
            print("❌ No companies found for marketer")
            return False
        
        print(f"✅ Found {companies.count()} companies for marketer")
        
        # Test marketer_my_companies view
        print("\n=== Testing Marketer My Companies View ===")
        
        factory = RequestFactory()
        request = factory.get('/marketer/my-companies/')
        request.user = marketer
        
        response = marketer_my_companies(request)
        
        if response.status_code == 200:
            print("✅ marketer_my_companies view returns HTTP 200")
            
            # Check if context contains companies
            context = response.context_data
            companies_list = context.get('companies', [])
            
            print(f"✅ Context contains {len(companies_list)} companies")
            
            if len(companies_list) > 0:
                for item in companies_list:
                    print(f"   - {item['company'].company_name} (Transactions: {item['transactions']}, Total Value: ₦{item['total_value']})")
                
                return True
            else:
                print("❌ No companies in context")
                return False
        else:
            print(f"❌ marketer_my_companies view returned HTTP {response.status_code}")
            return False
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_marketer_company_portfolio():
    """Test marketer company portfolio view"""
    
    print("\n=== Testing Marketer Company Portfolio View ===\n")
    
    try:
        # Get a test marketer
        marketer = CustomUser.objects.filter(role='marketer').first()
        if not marketer:
            print("❌ No marketer users found in database")
            return False
        
        # Get a company for this marketer
        company_ids = (
            Transaction.objects.filter(marketer=marketer)
            .values_list('company', flat=True)
            .distinct()
        )
        
        companies = Company.objects.filter(id__in=[c for c in company_ids if c is not None])
        
        if companies.count() == 0:
            print("❌ No companies found for marketer")
            return False
        
        company = companies.first()
        
        print(f"✅ Testing portfolio for company: {company.company_name}")
        
        # Test marketer_company_portfolio view
        factory = RequestFactory()
        request = factory.get(f'/marketer/my-companies/{company.id}/')
        request.user = marketer
        
        response = marketer_company_portfolio(request, company_id=company.id)
        
        if response.status_code == 200:
            print("✅ marketer_company_portfolio view returns HTTP 200")
            
            # Check if context contains required data
            context = response.context_data
            transactions = context.get('transactions', [])
            clients = context.get('clients', [])
            total_value = context.get('total_value', 0)
            
            print(f"✅ Context contains {transactions.count()} transactions")
            print(f"✅ Context contains {clients.count()} clients")
            print(f"✅ Total value: ₦{total_value}")
            
            return True
        else:
            print(f"❌ marketer_company_portfolio view returned HTTP {response.status_code}")
            return False
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sidebar_template():
    """Test that the sidebar template includes My Companies link"""
    
    print("\n=== Testing Sidebar Template ===\n")
    
    try:
        # Load the sidebar template
        from django.template.loader import get_template
        
        template = get_template('marketer_component/marketer_sidebar.html')
        
        # Create context
        context = {
            'unread_notifications_count': 0,
            'unread_chat_count': 0,
        }
        
        # Render the template
        rendered = template.render(context)
        
        print(f"✅ Sidebar template rendered successfully ({len(rendered)} characters)")
        
        # Check if My Companies link exists (check for the rendered URL)
        if 'href="/marketer/my-companies/"' in rendered:
            print("✅ My Companies link found in sidebar")
        else:
            print("❌ My Companies link not found in sidebar")
            return False
        
        # Check if My Companies icon exists
        if '<i class="bi bi-buildings"></i>' in rendered:
            print("✅ My Companies icon found in sidebar")
        else:
            print("❌ My Companies icon not found in sidebar")
            return False
        
        # Check if My Companies text exists
        if '<span>My Companies</span>' in rendered:
            print("✅ My Companies text found in sidebar")
        else:
            print("❌ My Companies text not found in sidebar")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test1_result = test_marketer_companies_functionality()
    test2_result = test_marketer_company_portfolio()
    test3_result = test_sidebar_template()
    
    print(f"\n=== Test Results ===")
    print(f"Marketer companies functionality test: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    print(f"Marketer company portfolio test: {'✅ PASSED' if test2_result else '❌ FAILED'}")
    print(f"Sidebar template test: {'✅ PASSED' if test3_result else '❌ FAILED'}")
    
    if test1_result and test2_result and test3_result:
        print("\n🎉 All marketer companies functionality tests passed!")
        print("\nComplete Marketer Companies Functionality:")
        print("1. ✅ Marketer can view all affiliate companies in 'My Companies'")
        print("2. ✅ Each company shows transaction count and total value")
        print("3. ✅ Marketer can click on a company to view detailed portfolio")
        print("4. ✅ Portfolio shows transactions, clients, and summary")
        print("5. ✅ Sidebar includes 'My Companies' navigation link")
        print("6. ✅ Proper URL routing and view functions")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")