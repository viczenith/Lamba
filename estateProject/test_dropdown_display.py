#!/usr/bin/env python
"""
Test that the dropdown shows all marketers with the new format
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from estateApp.views import user_registration
from estateApp.models import Company, CustomUser
import re

def test_dropdown_display():
    """
    Test that the dropdown shows all marketers with email and client count
    """
    print("\n" + "="*100)
    print("DROPDOWN DISPLAY TEST: All marketers with format 'Name • Email • X clients'")
    print("="*100 + "\n")
    
    # Get company
    company = Company.objects.filter(company_name='Lamba Real Homes').first()
    if not company:
        print("❌ Company not found")
        return False
    
    # Get admin user
    admin = CustomUser.objects.filter(
        company_profile=company,
        role='admin'
    ).first()
    
    if not admin:
        admin = CustomUser.objects.filter(role='admin').first()
    
    if not admin:
        print("❌ No admin user found")
        return False
    
    print(f"Setup:")
    print(f"  Company: {company.company_name}")
    print(f"  Admin: {admin.full_name}")
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get(f'/user-registration/?company={company.slug}')
    
    # Add middleware
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    
    middleware = AuthenticationMiddleware(lambda x: None)
    middleware.process_request(request)
    
    # Set user
    request.user = admin
    request.company = company
    
    # Call the view
    print(f"\nFetching response from view...")
    try:
        response = user_registration(request)
        if response.status_code != 200:
            print(f"❌ View returned status {response.status_code}")
            return False
        print(f"✅ View returned 200 OK")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Get the rendered content
    try:
        if hasattr(response, 'rendered_content'):
            html = response.rendered_content.decode('utf-8')
        elif hasattr(response, 'content'):
            html = response.content.decode('utf-8')
        else:
            print("❌ Cannot access response content")
            return False
    except Exception as e:
        print(f"❌ Error getting response content: {e}")
        return False
    
    print(f"✅ Got HTML response ({len(html)} bytes)")
    
    # Find the marketer select element
    print(f"\n🔍 Searching for marketer dropdown...")
    
    select_pattern = r'<select[^>]*id=["\']marketer["\'][^>]*>(.*?)</select>'
    match = re.search(select_pattern, html, re.DOTALL)
    
    if not match:
        print(f"❌ Could not find marketer select element")
        return False
    
    select_content = match.group(1)
    print(f"✅ Found marketer select element")
    
    # Extract all option tags
    option_pattern = r'<option[^>]*value=["\']([^"\']*)["\'][^>]*>([^<]*)</option>'
    options = re.findall(option_pattern, select_content)
    
    print(f"\n📋 Marketer Dropdown Options:")
    print(f"   Total options: {len(options)}")
    
    has_all_info = True
    for i, (value, text) in enumerate(options):
        if value == '':
            print(f"   0. [Default] {text}")
        else:
            print(f"   {i}. {text}")
            # Check if it has all required parts
            if '•' not in text:
                print(f"      ❌ Missing separator or info!")
                has_all_info = False
            # Parse the format: Name • Email • X clients
            parts = text.split(' • ')
            if len(parts) < 3:
                print(f"      ❌ Expected 3 parts (Name, Email, Clients) but got {len(parts)}")
                has_all_info = False
            elif len(parts) >= 3:
                name, email, clients = parts[0], parts[1], parts[2]
                print(f"      ✓ Name: {name}")
                print(f"      ✓ Email: {email}")
                print(f"      ✓ Clients: {clients}")
    
    if not has_all_info:
        print(f"\n❌ Not all options have the correct format")
        return False
    
    # Check count of marketers
    rendered_count = len(options) - 1  # -1 for default
    print(f"\n✅ All {rendered_count} marketers displaying with enhanced format!")
    
    if rendered_count < 4:
        print(f"❌ Expected 4 marketers but got {rendered_count}")
        return False
    
    print(f"\n" + "="*100)
    print(f"RESULT: ✅ DROPDOWN DISPLAY TEST PASSED")
    print(f"="*100 + "\n")
    
    return True

if __name__ == '__main__':
    try:
        success = test_dropdown_display()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
