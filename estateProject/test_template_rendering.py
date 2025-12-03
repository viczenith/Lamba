#!/usr/bin/env python3
"""
Test script to verify template rendering for chat companies
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.template import Context, Template
from estateApp.models import Company, CustomUser, PlotAllocation

def test_template_rendering():
    """Test that the template renders companies correctly"""
    
    print("=== Testing Template Rendering ===\n")
    
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
        
        # Test template rendering
        template_str = '''
{% for company in companies %}
    <div class="explorer-item" data-company-id="{{ company.id }}" data-company-name="{{ company.company_name }}">
        {{ company.company_name }}
    </div>
{% endfor %}
'''
        
        template = Template(template_str)
        context = Context({'companies': companies})
        rendered = template.render(context)
        
        print(f"\n✅ Template rendered successfully:")
        print(rendered)
        
        # Check if the rendered output contains company names
        if companies.count() > 0:
            for company in companies:
                if company.company_name in rendered:
                    print(f"✅ Company '{company.company_name}' found in rendered output")
                else:
                    print(f"❌ Company '{company.company_name}' NOT found in rendered output")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    result = test_template_rendering()
    print(f"\n=== Test Result ===")
    print(f"Template rendering test: {'✅ PASSED' if result else '❌ FAILED'}")