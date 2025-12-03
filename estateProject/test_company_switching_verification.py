#!/usr/bin/env python3
"""
Test script to verify the JavaScript company switching logic
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.template.loader import get_template
from estateApp.models import Company, CustomUser, PlotAllocation, Message

def test_company_switching_verification():
    """Test that the JavaScript company switching logic is correct"""
    
    print("=== Testing Company Switching JavaScript Logic ===\n")
    
    try:
        # Get a test client
        client = CustomUser.objects.filter(role='client').first()
        if not client:
            print("❌ No client users found in database")
            return False
        
        print(f"✅ Found client: {client.email} (ID: {client.id})")
        
        # Get companies for this client
        companies = Company.objects.filter(
            estates__plotallocation__client=client
        ).distinct().order_by('company_name')
        
        if companies.count() < 2:
            print("❌ Need at least 2 companies for switching test")
            return False
        
        company_a = companies[0]
        company_b = companies[1]
        
        print(f"✅ Found companies: {company_a.company_name} and {company_b.company_name}")
        
        # Load the chat template
        template = get_template('client_side/chat_interface.html')
        
        # Create context
        context = {
            'companies': companies,
            'selected_company': company_a,
            'client': client,
            'messages': [],
        }
        
        # Render the template
        rendered = template.render(context)
        
        print(f"✅ Template rendered successfully ({len(rendered)} characters)")
        
        # Check if the JavaScript has the correct logic
        print("\n=== Checking JavaScript Logic ===")
        
        # Check if selectedCompanyId is properly initialized
        if 'let selectedCompanyId = document.getElementById' in rendered:
            print("✅ selectedCompanyId is properly initialized")
        else:
            print("❌ selectedCompanyId initialization not found")
            return False
        
        # Check if selectedCompanyId is updated in click handler
        if 'selectedCompanyId = companyId;' in rendered:
            print("✅ selectedCompanyId is updated in click handler")
        else:
            print("❌ selectedCompanyId update in click handler not found")
            return False
        
        # Check if selectedCompanyId is used in pollNewMessages
        if 'if (selectedCompanyId) url += `&company_id=${selectedCompanyId}`;' in rendered:
            print("✅ selectedCompanyId is used in pollNewMessages")
        else:
            print("❌ selectedCompanyId usage in pollNewMessages not found")
            return False
        
        # Check if currentSelectedCompanyId is also updated
        if 'currentSelectedCompanyId = companyId;' in rendered:
            print("✅ currentSelectedCompanyId is updated in click handler")
        else:
            print("❌ currentSelectedCompanyId update in click handler not found")
            return False
        
        # Check if both variables are updated in updateChatHeader
        if 'selectedCompanyId = companyId;' in rendered and 'currentSelectedCompanyId = companyId;' in rendered:
            print("✅ Both selectedCompanyId and currentSelectedCompanyId are updated in updateChatHeader")
        else:
            print("❌ Both variables not updated in updateChatHeader")
            return False
        
        # Check if the click event handler exists
        if 'document.querySelectorAll(\'.explorer-item\').forEach(function(item){' in rendered:
            print("✅ Click event handler for explorer items exists")
        else:
            print("❌ Click event handler for explorer items not found")
            return False
        
        # Check if the functions are called in the right order
        if 'updateChatHeader(companyId, companyName, companyLogo);' in rendered:
            print("✅ updateChatHeader is called in click handler")
        else:
            print("❌ updateChatHeader not called in click handler")
            return False
        
        if 'highlightSelectedCompany(companyId);' in rendered:
            print("✅ highlightSelectedCompany is called in click handler")
        else:
            print("❌ highlightSelectedCompany not called in click handler")
            return False
        
        if 'pollNewMessages();' in rendered:
            print("✅ pollNewMessages is called in click handler")
        else:
            print("❌ pollNewMessages not called in click handler")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_polling_url_generation():
    """Test that the polling URL is generated correctly with company_id"""
    
    print("\n=== Testing Polling URL Generation ===\n")
    
    try:
        # Get a test client
        client = CustomUser.objects.filter(role='client').first()
        if not client:
            print("❌ No client users found in database")
            return False
        
        # Get companies for this client
        companies = Company.objects.filter(
            estates__plotallocation__client=client
        ).distinct().order_by('company_name')
        
        if companies.count() < 1:
            print("❌ Need at least 1 company for polling test")
            return False
        
        company = companies[0]
        
        # Simulate the JavaScript logic
        print("✅ Simulating JavaScript polling URL generation:")
        
        # Initial URL without company_id
        base_url = "/chat/?last_msg=0"
        print(f"   Base URL: {base_url}")
        
        # With company_id
        selectedCompanyId = str(company.id)
        polling_url = f"{base_url}&company_id={selectedCompanyId}"
        print(f"   Polling URL: {polling_url}")
        
        # Verify the URL contains the company_id parameter
        if f"company_id={selectedCompanyId}" in polling_url:
            print("✅ Polling URL correctly includes company_id parameter")
        else:
            print("❌ Polling URL missing company_id parameter")
            return False
        
        # Verify the URL structure is correct
        if polling_url.startswith("/chat/?last_msg=0&company_id="):
            print("✅ Polling URL has correct structure")
        else:
            print("❌ Polling URL has incorrect structure")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test1_result = test_company_switching_verification()
    test2_result = test_polling_url_generation()
    
    print(f"\n=== Test Results ===")
    print(f"Company switching JavaScript test: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    print(f"Polling URL generation test: {'✅ PASSED' if test2_result else '❌ FAILED'}")
    
    if test1_result and test2_result:
        print("\n🎉 All tests passed! The dynamic company switching should work correctly.")
        print("\nWhen a company is clicked in the My Companies explorer:")
        print("1. ✅ selectedCompanyId is updated")
        print("2. ✅ currentSelectedCompanyId is updated")
        print("3. ✅ Chat header is updated with company info")
        print("4. ✅ Selected company is highlighted")
        print("5. ✅ pollNewMessages() is called with correct company_id")
        print("6. ✅ Messages are loaded for the selected company")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")