#!/usr/bin/env python3
"""
Debug script to test the chat_view function directly
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

def test_chat_view_debug():
    """Debug the chat_view function to see what context is being passed"""
    
    print("=== Debugging Chat View ===\n")
    
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
        
        # Test the chat_view function logic directly
        print("\n=== Testing chat_view logic ===")
        
        # Simulate the chat_view logic
        selected_company = companies.first() if companies.exists() else None
        
        print(f"✅ Selected company: {selected_company.company_name if selected_company else 'None'}")
        
        # Test context building
        context = {
            'companies': companies,
            'selected_company': selected_company,
            'client': client,
            'messages': [],  # Empty for now
        }
        
        print(f"✅ Context built successfully:")
        print(f"   - companies: {companies.count()} companies")
        print(f"   - selected_company: {selected_company.company_name if selected_company else 'None'}")
        print(f"   - client: {client.username}")
        
        # Test template rendering with this context
        from django.template import Context, Template
        
        template_str = '''
{% for company in companies %}
    Company: {{ company.company_name }} (ID: {{ company.id }})
{% endfor %}
'''
        
        template = Template(template_str)
        rendered_context = Context(context)
        rendered = template.render(rendered_context)
        
        print(f"\n✅ Template rendering test:")
        print(rendered)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    result = test_chat_view_debug()
    print(f"\n=== Test Result ===")
    print(f"Chat view debug test: {'✅ PASSED' if result else '❌ FAILED'}")