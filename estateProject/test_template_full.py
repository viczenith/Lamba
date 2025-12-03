#!/usr/bin/env python3
"""
Test script to verify full template rendering
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
from estateApp.models import Company, CustomUser, PlotAllocation

def test_full_template_rendering():
    """Test full template rendering"""
    
    print("=== Testing Full Template Rendering ===\n")
    
    try:
        # Get a test client
        client = CustomUser.objects.filter(role='client').first()
        if not client:
            print("❌ No client users found in database")
            return False
        
        print(f"✅ Found client: {client.username} (ID: {client.id})")
        
        # Get companies for this client
        companies = Company.objects.filter(
            estates__plotallocation__client=client
        ).distinct().order_by('company_name')
        
        print(f"✅ Found {companies.count()} companies:")
        for company in companies:
            print(f"   - {company.company_name} (ID: {company.id})")
        
        # Load the template
        template = get_template('client_side/chat_interface.html')
        
        # Create context
        context = {
            'companies': companies,
            'selected_company': companies.first() if companies.exists() else None,
            'client': client,
            'messages': [],
        }
        
        # Render the template
        rendered = template.render(context)
        
        print(f"✅ Template rendered successfully ({len(rendered)} characters)")
        
        # Check if companies are in the rendered output
        print("\n=== Checking companies in rendered output ===")
        for company in companies:
            if str(company.id) in rendered:
                print(f"✅ Company {company.company_name} (ID: {company.id}) found in rendered output")
            else:
                print(f"❌ Company {company.company_name} (ID: {company.id}) NOT found in rendered output")
        
        # Save rendered output to file for inspection
        with open('rendered_chat.html', 'w', encoding='utf-8') as f:
            f.write(rendered)
        
        print(f"\n✅ Rendered template saved to rendered_chat.html")
        
        # Check for specific patterns in the rendered output
        if 'explorer-item' in rendered:
            print("✅ Explorer items found in rendered output")
        else:
            print("❌ Explorer items NOT found in rendered output")
        
        if 'data-company-id' in rendered:
            print("✅ Company IDs found in rendered output")
        else:
            print("❌ Company IDs NOT found in rendered output")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    result = test_full_template_rendering()
    print(f"\n=== Test Result ===")
    print(f"Full template rendering test: {'✅ PASSED' if result else '❌ FAILED'}")