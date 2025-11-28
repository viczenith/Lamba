#!/usr/bin/env python
"""
Targeted test for multi-company add-existing-user issue using REAL DATA.

Tests with:
- Company A: Lamba Property Limited
- Company B: Lamba Real Homes (NEW - less tested)
- Test user: testclient@example.com (unassigned client)
- Marketers: victorgodwinakor, akorvikkyy (already in Company A)
"""

import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from estateApp.models import Company, CustomUser, MarketerUser, ClientUser
from django.test import RequestFactory
from estateApp.views import add_existing_user_to_company

print("\n" + "█"*80)
print("█  MULTI-COMPANY ADD-EXISTING-USER: FOCUSED TEST")
print("█  Using REAL DATA from existing companies")
print("█"*80 + "\n")

# Companies
lpl = Company.objects.get(company_name='Lamba Property Limited')  # Company A
lrh = Company.objects.get(company_name='Lamba Real Homes')  # Company B

print(f"Company A: {lpl.company_name} (ID: {lpl.id})")
print(f"Company B: {lrh.company_name} (ID: {lrh.id})\n")

# Get admins
admin_a = CustomUser.objects.filter(company_profile=lpl, role='admin').first()
admin_b = CustomUser.objects.filter(company_profile=lrh, role='admin').first()

print(f"Admin A: {admin_a.email} -> {admin_a.company_profile.company_name}")
print(f"Admin B: {admin_b.email} -> {admin_b.company_profile.company_name}\n")

# Get test user
test_user = CustomUser.objects.get(email='testclient@example.com')
print(f"Test User: {test_user.email}")
print(f"  - Role: {test_user.role}")
print(f"  - Company Profile: {test_user.company_profile}\n")

# Get a marketer from Company A (will use for assignment)
marketer_a = MarketerUser.objects.filter(company_profile=lpl).first()
print(f"Marketer A (from Company A): {marketer_a.email} (ID: {marketer_a.id})\n")

# Create factory for requests
factory = RequestFactory()

def test_add_user(admin, company, marketer):
    """Test adding the test user to a company"""
    company_name = company.company_name
    print(f"\n{'='*70}")
    print(f"TEST: Adding {test_user.email} to {company_name}")
    print(f"  Admin: {admin.email}")
    print(f"  Marketer: {marketer.email}")
    print(f"{'='*70}\n")
    
    # Prepare payload
    payload = {
        'user_id': test_user.id,
        'marketer_id': marketer.id
    }
    
    # Create mock request
    request = factory.post(
        '/api/add-existing-user-to-company/',
        data=json.dumps(payload),
        content_type='application/json'
    )
    request.user = admin
    
    print(f"Request context:")
    print(f"  - request.user: {request.user.email}")
    print(f"  - request.user.company_profile: {request.user.company_profile.company_name if request.user.company_profile else 'NULL'}")
    print(f"  - request.user.role: {request.user.role}\n")
    
    print(f"Payload:")
    print(f"  - user_id: {payload['user_id']}")
    print(f"  - marketer_id: {payload['marketer_id']}\n")
    
    try:
        response = add_existing_user_to_company(request)
        data = json.loads(response.content)
        status_code = response.status_code
        
        print(f"Response (HTTP {status_code}):")
        
        if 'error' in data:
            print(f"  ❌ ERROR: {data['error']}")
            if 'existing' in data:
                print(f"     (User already in company)")
                print(f"     Role: {data.get('role')}")
                print(f"     Company: {data.get('company')}")
        elif 'success' in data and data['success']:
            print(f"  ✅ SUCCESS!")
            print(f"     Message: {data.get('message')}")
            print(f"     User ID: {data['user']['id']}")
            print(f"     User Email: {data['user']['email']}")
            print(f"     Company: {data['user']['company']}")
        else:
            print(f"  ❓ UNEXPECTED: {data}")
            
    except Exception as e:
        import traceback
        print(f"  ❌ EXCEPTION: {str(e)}")
        traceback.print_exc()
    
    # Verify user was added to company
    test_user.refresh_from_db()
    print(f"\nUser state after request:")
    print(f"  - Test user company_profile: {test_user.company_profile}")
    if test_user.company_profile:
        print(f"     Company: {test_user.company_profile.company_name}")


# TEST 1: Add to Company A (should work - LPL is primary)
print("\n" + "█"*80)
print("█  TEST 1: ADD TO COMPANY A (Lamba Property Limited)")
print("█"*80)

try:
    test_add_user(admin_a, lpl, marketer_a)
except Exception as e:
    print(f"\n❌ Test 1 FAILED: {str(e)}")
    import traceback
    traceback.print_exc()

# Reset test user for test 2
print("\n\n⚠️  RESETTING TEST USER...\n")
test_user.company_profile = None
test_user.save()
test_user.refresh_from_db()
print(f"Test user company_profile: {test_user.company_profile}")

# TEST 2: Add to Company B (the problematic one)
print("\n" + "█"*80)
print("█  TEST 2: ADD TO COMPANY B (Lamba Real Homes)")
print("█"*80)

# Get a marketer from Company B (or use the one from A)
marketer_b = MarketerUser.objects.filter(company_profile=lrh).first()
if not marketer_b:
    print(f"\n⚠️  No marketer in Company B, using marketer from Company A: {marketer_a.email}")
    marketer_b = marketer_a
else:
    print(f"\nFound marketer in Company B: {marketer_b.email}")

try:
    test_add_user(admin_b, lrh, marketer_b)
except Exception as e:
    print(f"\n❌ Test 2 FAILED: {str(e)}")
    import traceback
    traceback.print_exc()

# Final summary
print("\n\n" + "█"*80)
print("█  FINAL RESULTS")
print("█"*80 + "\n")

test_user.refresh_from_db()
print(f"Final Test User State:")
print(f"  - Email: {test_user.email}")
print(f"  - company_profile: {test_user.company_profile}")
if test_user.company_profile:
    print(f"  - Company: {test_user.company_profile.company_name}")

# Check if user appears in both company lists
print(f"\nChecking user in company rosters:")
in_lpl = ClientUser.objects.filter(id=test_user.id, company_profile=lpl).exists()
in_lrh = ClientUser.objects.filter(id=test_user.id, company_profile=lrh).exists()
print(f"  - In Lamba Property Limited: {'✅ YES' if in_lpl else '❌ NO'}")
print(f"  - In Lamba Real Homes: {'✅ YES' if in_lrh else '❌ NO'}")

print("\n" + "█"*80)
print("█  TEST COMPLETE")
print("█"*80 + "\n")
