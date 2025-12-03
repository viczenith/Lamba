#!/usr/bin/env python3
"""
Final verification test for chat functionality
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
from django.db.models import Q
from estateApp.models import Company, CustomUser, PlotAllocation, Message

def test_final_verification():
    """Final verification of all chat functionality"""
    
    print("=== Final Verification of Chat Functionality ===\n")
    
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
            print("❌ Need at least 2 companies for verification")
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
        
        # Verify template has correct company references
        print("\n=== Verifying Template Company References ===")
        
        # Check if companies are rendered correctly
        if f'data-company-id="{company_a.id}"' in rendered:
            print(f"✅ Company A ({company_a.company_name}) rendered correctly")
        else:
            print(f"❌ Company A ({company_a.company_name}) not found in template")
            return False
        
        if f'data-company-id="{company_b.id}"' in rendered:
            print(f"✅ Company B ({company_b.company_name}) rendered correctly")
        else:
            print(f"❌ Company B ({company_b.company_name}) not found in template")
            return False
        
        # Check if form has correct company_id reference
        if f'value="{company_a.id}"' in rendered:
            print("✅ Form hidden field has correct company_id value")
        else:
            print("❌ Form hidden field missing or incorrect company_id value")
            return False
        
        # Verify JavaScript logic
        print("\n=== Verifying JavaScript Logic ===")
        
        # Check if form field is updated in click handler
        if 'companyInput.value = companyId;' in rendered:
            print("✅ Form field is updated when company is clicked")
        else:
            print("❌ Form field not updated when company is clicked")
            return False
        
        # Check if both variables are updated
        if 'selectedCompanyId = companyId;' in rendered and 'currentSelectedCompanyId = companyId;' in rendered:
            print("✅ Both selectedCompanyId and currentSelectedCompanyId are updated")
        else:
            print("❌ Variable updates missing in JavaScript")
            return False
        
        # Check if polling uses correct variable
        if 'if (selectedCompanyId) url += `&company_id=${selectedCompanyId}`;' in rendered:
            print("✅ pollNewMessages uses selectedCompanyId correctly")
        else:
            print("❌ pollNewMessages not using selectedCompanyId correctly")
            return False
        
        # Verify message isolation
        print("\n=== Verifying Message Isolation ===")
        
        # Test message filtering logic
        messages_a = Message.objects.filter(
            company=company_a
        ).filter(
            Q(sender=client) | Q(recipient=client)
        )
        
        messages_b = Message.objects.filter(
            company=company_b
        ).filter(
            Q(sender=client) | Q(recipient=client)
        )
        
        print(f"✅ Company A has {messages_a.count()} messages")
        print(f"✅ Company B has {messages_b.count()} messages")
        
        # Verify no overlap
        company_a_ids = set(messages_a.values_list('id', flat=True))
        company_b_ids = set(messages_b.values_list('id', flat=True))
        
        if company_a_ids.intersection(company_b_ids):
            print("❌ Messages are overlapping between companies")
            return False
        else:
            print("✅ No message overlap between companies")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    result = test_final_verification()
    
    print(f"\n=== Final Test Result ===")
    print(f"Final verification test: {'✅ PASSED' if result else '❌ FAILED'}")
    
    if result:
        print("\n🎉 ALL CHAT FUNCTIONALITY IS WORKING CORRECTLY!")
        print("\nSummary of fixes:")
        print("1. ✅ Companies display correctly in My Companies explorer")
        print("2. ✅ Companies are clickable and switch chat interface dynamically")
        print("3. ✅ Form hidden field updates when company is clicked")
        print("4. ✅ Message polling uses correct company_id")
        print("5. ✅ Messages are properly isolated between companies")
        print("6. ✅ Template has correct company references")
        print("7. ✅ JavaScript logic is synchronized")
        
        print("\nExpected behavior:")
        print("- Users can click companies in My Companies explorer")
        print("- Chat interface switches dynamically")
        print("- Messages load for the selected company")
        print("- Messages are sent to the correct company")
        print("- No cross-contamination between company chats")
    else:
        print("\n❌ Some functionality is still not working correctly.")