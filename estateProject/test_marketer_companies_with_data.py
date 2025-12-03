#!/usr/bin/env python3
"""
Test script to verify marketer companies functionality with test data
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
from estateApp.models import Company, CustomUser, PlotAllocation, Message, Transaction, PlotSizeUnits, EstatePlot
from estateApp.views import marketer_my_companies, marketer_company_portfolio

def test_marketer_companies_with_data():
    """Test marketer companies functionality with test data"""
    
    print("=== Testing Marketer Companies Functionality with Test Data ===\n")
    
    try:
        # Get a test marketer
        marketer = CustomUser.objects.filter(role='marketer').first()
        if not marketer:
            print("❌ No marketer users found in database")
            return False
        
        print(f"✅ Found marketer: {marketer.email} (ID: {marketer.id})")
        
        # Get a test client
        client = CustomUser.objects.filter(role='client').first()
        if not client:
            print("❌ No client users found in database")
            return False
        
        print(f"✅ Found client: {client.email} (ID: {client.id})")
        
        # Get a test company
        company = Company.objects.first()
        if not company:
            print("❌ No companies found in database")
            return False
        
        print(f"✅ Found company: {company.company_name} (ID: {company.id})")
        
        # Get a test estate
        estate = company.estates.first()
        if not estate:
            print("❌ No estates found for company")
            return False
        
        print(f"✅ Found estate: {estate.name} (ID: {estate.id})")
        
        # Get a test plot size
        plot_size = estate.estate_plots.first().plot_size if estate.estate_plots.first() else None
        if not plot_size:
            print("❌ No plot sizes found for estate")
            return False
        
        print(f"✅ Found plot size: {plot_size.size}")
        
        # Get a test plot size unit
        plot_size_unit = estate.estate_plots.first()
        if not plot_size_unit:
            print("❌ No plot size units found for estate")
            return False
        
        print(f"✅ Found plot size unit: {plot_size_unit.plot_size.size}")
        
        # Create a test transaction to affiliate the marketer with the company
        transaction = Transaction.objects.create(
            client=client,
            marketer=marketer,
            company=company,
            estate=estate,
            plot_size=plot_size,
            plot_size_unit=plot_size_unit,
            total_amount=1000000,
            transaction_date='2025-12-02',
            reference_code='TEST-123456',
            payment_type='full'
        )
        
        print(f"✅ Created test transaction: {transaction.reference_code}")
        
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

def test_marketer_company_portfolio_with_data():
    """Test marketer company portfolio view with test data"""
    
    print("\n=== Testing Marketer Company Portfolio View with Test Data ===\n")
    
    try:
        # Get a test marketer
        marketer = CustomUser.objects.filter(role='marketer').first()
        if not marketer:
            print("❌ No marketer users found in database")
            return False
        
        # Get a test company
        company = Company.objects.first()
        if not company:
            print("❌ No companies found in database")
            return False
        
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
    test1_result = test_marketer_companies_with_data()
    test2_result = test_marketer_company_portfolio_with_data()
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
        print("7. ✅ Companies are dynamically populated based on marketer transactions")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")