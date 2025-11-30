#!/usr/bin/env python
"""
Test to verify that the template is actually rendering all marketers in the select options
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import RequestFactory, Client
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from estateApp.views import user_registration
from estateApp.models import Company, CustomUser, MarketerAffiliation
import re

def test_template_rendering():
    """
    Simulate the actual request and check the HTML response
    to see if all marketer options are rendered
    """
    print("\n" + "="*100)
    print("TEMPLATE RENDERING TEST: Checking actual HTML output")
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
    
    print(f"✅ Setup:")
    print(f"   Company: {company.company_name}")
    print(f"   Admin: {admin.full_name}")
    
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
    print(f"\n📄 Fetching response from view...")
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
    print(f"\n🔍 Searching for marketer dropdown in HTML...")
    
    # Pattern to find all <option> tags in the marketer select
    select_pattern = r'<select[^>]*id=["\']marketer["\'][^>]*>(.*?)</select>'
    match = re.search(select_pattern, html, re.DOTALL)
    
    if not match:
        print(f"❌ Could not find marketer select element")
        # Debug: Show part of HTML
        if 'id="marketer"' in html:
            print(f"   (But 'id=\"marketer\"' was found in HTML)")
            idx = html.find('id="marketer"')
            print(f"   Context: ...{html[max(0, idx-100):idx+200]}...")
        return False
    
    select_content = match.group(1)
    print(f"✅ Found marketer select element")
    
    # Extract all option tags
    option_pattern = r'<option[^>]*value=["\']([^"\']*)["\'][^>]*>([^<]*)</option>'
    options = re.findall(option_pattern, select_content)
    
    print(f"\n📋 Marketer Options Rendered in HTML:")
    print(f"   Total options: {len(options)}")
    
    for i, (value, text) in enumerate(options):
        if value == '':
            print(f"   0. [Default] {text}")
        else:
            print(f"   {i}. ID={value}, Name={text}")
    
    # Get expected marketers
    print(f"\n📊 Expected vs Actual:")
    
    marketers_primary = CustomUser.objects.filter(role='marketer', company_profile=company)
    affiliation_marketer_ids = MarketerAffiliation.objects.filter(
        company=company
    ).values_list('marketer_id', flat=True).distinct()
    marketers_affiliated = CustomUser.objects.filter(
        id__in=affiliation_marketer_ids
    ).exclude(
        id__in=marketers_primary.values_list('pk', flat=True)
    )
    
    expected_marketers = list(marketers_primary) + list(marketers_affiliated)
    
    print(f"   Expected count (backend): {len(expected_marketers)}")
    print(f"   Rendered count (HTML): {len(options) - 1}")  # -1 for default option
    
    if len(expected_marketers) != len(options) - 1:
        print(f"\n   ❌ MISMATCH: Backend has {len(expected_marketers)} but HTML has {len(options)-1}")
        
        print(f"\n   Expected marketers:")
        for m in expected_marketers:
            print(f"      - ID={m.id}, Name={m.full_name}, Email={m.email}")
        
        print(f"\n   Rendered in HTML:")
        for value, text in options[1:]:  # Skip default
            print(f"      - ID={value}, Name={text}")
        
        return False
    else:
        print(f"\n   ✅ COUNT MATCHES!")
    
    # Check if all expected marketers are rendered
    rendered_ids = set(value for value, _ in options[1:])
    expected_ids = set(m.id for m in expected_marketers)
    
    missing = expected_ids - rendered_ids
    extra = rendered_ids - expected_ids
    
    if missing:
        print(f"\n   ❌ Missing in HTML: {missing}")
        return False
    
    if extra:
        print(f"\n   ❌ Extra in HTML: {extra}")
        return False
    
    print(f"\n   ✅ All expected marketers are in HTML!")
    print(f"\n" + "="*100)
    print(f"RESULT: ✅ TEMPLATE RENDERING TEST PASSED")
    print(f"="*100 + "\n")
    
    return True

if __name__ == '__main__':
    try:
        success = test_template_rendering()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
