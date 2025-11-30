#!/usr/bin/env python
"""
Test the actual HTTP request flow through Django test client
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from estateApp.models import Company, CustomUser, MarketerAffiliation
import re

def test_actual_http():
    """
    Test through actual Django test client to see how middleware affects it
    """
    print("\n" + "="*100)
    print("ACTUAL HTTP REQUEST TEST")
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
        print("❌ No admin user found")
        return False
    
    print(f"Setup:")
    print(f"  Company: {company.company_name} (ID: {company.id}, slug: {company.slug})")
    print(f"  Admin: {admin.full_name} (ID: {admin.id}, role: {admin.role})")
    
    # Use Django test client
    client = Client()
    
    # Login
    print(f"\nLogging in...")
    login_ok = client.login(username=admin.email, password='12345')
    if not login_ok:
        print(f"❌ Login failed - trying with username instead")
        login_ok = client.login(username=admin.username, password='password')
    
    if not login_ok:
        print(f"❌ Login failed")
        print(f"   Email: {admin.email}")
        print(f"   Username: {admin.username}")
        # Try to find a user for testing
        all_admins = CustomUser.objects.filter(role='admin')
        print(f"   Available admins: {[u.email for u in all_admins[:3]]}")
        return False
    
    print(f"✅ Logged in")
    
    # Get the page
    print(f"\nFetching /user-registration/ with slug...")
    url = f'/{company.slug}/user-registration/'
    response = client.get(url)
    
    print(f"Response status: {response.status_code}")
    if response.status_code != 200:
        print(f"❌ Unexpected status code")
        return False
    
    # Get HTML
    html = response.content.decode('utf-8')
    print(f"✅ Got HTML ({len(html)} bytes)")
    
    # Find marketer options
    print(f"\nSearching for marketer select...")
    select_pattern = r'<select[^>]*id=["\']marketer["\'][^>]*>(.*?)</select>'
    match = re.search(select_pattern, html, re.DOTALL)
    
    if not match:
        print(f"❌ Could not find marketer select")
        return False
    
    select_content = match.group(1)
    option_pattern = r'<option[^>]*value=["\']([^"\']*)["\'][^>]*>([^<]*)</option>'
    options = re.findall(option_pattern, select_content)
    
    print(f"\nMarketer Options in HTML:")
    print(f"  Total options: {len(options)}")
    for i, (value, text) in enumerate(options):
        if value == '':
            print(f"    0. [Default] {text}")
        else:
            print(f"    {i}. ID={value}, Name={text}")
    
    # Expected
    marketers_primary = CustomUser.objects.filter(role='marketer', company_profile=company)
    affiliation_marketer_ids = MarketerAffiliation.objects.filter(
        company=company
    ).values_list('marketer_id', flat=True).distinct()
    marketers_affiliated = CustomUser.objects.filter(
        id__in=affiliation_marketer_ids
    ).exclude(
        id__in=marketers_primary.values_list('pk', flat=True)
    )
    
    expected_count = marketers_primary.count() + marketers_affiliated.count()
    rendered_count = len(options) - 1  # -1 for default
    
    print(f"\nExpected: {expected_count}, Rendered: {rendered_count}")
    
    if expected_count == rendered_count:
        print(f"✅ PASS")
        return True
    else:
        print(f"❌ FAIL")
        return False

if __name__ == '__main__':
    try:
        success = test_actual_http()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
