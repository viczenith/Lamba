#!/usr/bin/env python
"""
Test script to diagnose multi-company add-existing-user issue.

Reproduces: "IT ADDS FOR COMPANY A BUT NOT ADDING FOR COMPANY B"

Tests:
1. Check if both companies exist and have proper admin users
2. Check if admin users have correct company_profile set
3. Simulate add-existing-user API call for each company
4. Identify which step fails for Company B
"""

import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from estateApp.models import Company, CustomUser, MarketerUser, ClientUser
from django.utils import timezone
from datetime import timedelta
import json


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def diagnose_companies():
    """Check all companies and their admin users"""
    print_section("STEP 1: COMPANIES & ADMINS DIAGNOSIS")
    
    companies = Company.objects.all()
    print(f"\n📊 Total Companies: {companies.count()}\n")
    
    for idx, company in enumerate(companies, 1):
        print(f"{idx}. Company: {company.company_name} (ID: {company.id})")
        print(f"   Status: {company.subscription_status}")
        print(f"   Trial Ends: {company.trial_ends_at}")
        
        # Find admin users for this company
        admin = CustomUser.objects.filter(company_profile=company, role='admin').first()
        if admin:
            print(f"   ✅ Admin User: {admin.email} (ID: {admin.id})")
            print(f"      - company_profile: {admin.company_profile.company_name if admin.company_profile else 'NULL'}")
            print(f"      - is_active: {admin.is_active}")
            print(f"      - is_deleted: {admin.is_deleted}")
        else:
            print(f"   ❌ NO ADMIN USER FOUND")


def diagnose_users():
    """Check all registered users and their company assignments"""
    print_section("STEP 2: REGISTERED USERS & COMPANY ASSIGNMENTS")
    
    users = CustomUser.objects.filter(is_active=True, is_deleted=False)
    print(f"\n📊 Total Active Users: {users.count()}\n")
    
    by_company = {}
    by_role = {'client': [], 'marketer': [], 'admin': [], 'support': []}
    
    for user in users:
        company_name = user.company_profile.company_name if user.company_profile else "UNASSIGNED"
        role = user.role or "NO_ROLE"
        
        if company_name not in by_company:
            by_company[company_name] = []
        by_company[company_name].append(user)
        
        if role in by_role:
            by_role[role].append(user)
    
    print("📌 Users by Company:")
    for company_name, company_users in sorted(by_company.items()):
        print(f"\n   {company_name}: {len(company_users)} users")
        for user in company_users:
            print(f"      - {user.email} ({user.role})")
    
    print("\n\n📌 Users by Role:")
    for role, role_users in by_role.items():
        print(f"\n   {role.upper()}: {len(role_users)} users")
        for user in role_users[:5]:
            company = user.company_profile.company_name if user.company_profile else "UNASSIGNED"
            print(f"      - {user.email} ({company})")


def test_search_isolation():
    """Test if search_existing_users_api works for both companies"""
    print_section("STEP 3: SEARCH EXISTING USERS - ISOLATION TEST")
    
    from estateApp.views import search_existing_users_api
    from django.test import RequestFactory
    
    factory = RequestFactory()
    companies = list(Company.objects.all())[:2]
    
    if len(companies) < 2:
        print("\n❌ Not enough companies to test (need at least 2)")
        return
    
    for company in companies:
        print(f"\n\n🔍 Testing Company: {company.company_name} (ID: {company.id})")
        
        # Get admin for this company
        admin = CustomUser.objects.filter(company_profile=company, role='admin').first()
        if not admin:
            print(f"   ❌ No admin user for {company.company_name}")
            continue
        
        print(f"   Admin: {admin.email} (ID: {admin.id})")
        print(f"   Admin company_profile: {admin.company_profile.company_name if admin.company_profile else 'NULL'}")
        
        # Create mock request
        request = factory.get('/api/search-existing-users/?q=test&role=client')
        request.user = admin
        
        try:
            response = search_existing_users_api(request)
            data = json.loads(response.content)
            
            if 'error' in data:
                print(f"   ❌ API ERROR: {data['error']}")
            else:
                users_found = data.get('users', [])
                print(f"   ✅ Search works - Found {len(users_found)} users")
                if len(users_found) > 0:
                    for user in users_found[:3]:
                        print(f"      - {user['email']} ({user['role']})")
        except Exception as e:
            print(f"   ❌ EXCEPTION: {str(e)}")


def test_add_isolation():
    """Test if add_existing_user_to_company works for both companies"""
    print_section("STEP 4: ADD EXISTING USER - ISOLATION TEST")
    
    from estateApp.views import add_existing_user_to_company
    from django.test import RequestFactory
    
    factory = RequestFactory()
    companies = list(Company.objects.all())[:2]
    
    if len(companies) < 2:
        print("\n❌ Not enough companies to test (need at least 2)")
        return
    
    # Find a user that's unassigned or assigned to only one company
    unassigned_user = CustomUser.objects.filter(
        is_active=True, 
        is_deleted=False, 
        company_profile__isnull=True
    ).first()
    
    if not unassigned_user:
        print("\n❌ No unassigned users found to test with")
        return
    
    print(f"\nUsing test user: {unassigned_user.email} (ID: {unassigned_user.id})")
    print(f"Test user role: {unassigned_user.role}")
    print(f"Test user company_profile: {unassigned_user.company_profile}")
    
    for company in companies:
        print(f"\n\n➕ Testing Add Existing User for: {company.company_name} (ID: {company.id})")
        
        # Get admin for this company
        admin = CustomUser.objects.filter(company_profile=company, role='admin').first()
        if not admin:
            print(f"   ❌ No admin user for {company.company_name}")
            continue
        
        print(f"   Admin: {admin.email}")
        print(f"   Admin company_profile: {admin.company_profile}")
        print(f"   Admin company_profile.company_name: {admin.company_profile.company_name if admin.company_profile else 'NULL'}")
        
        # Prepare payload
        payload = {'user_id': unassigned_user.id}
        if unassigned_user.role == 'client':
            # Get a marketer for this company
            marketer = MarketerUser.objects.filter(company_profile=company).first()
            if marketer:
                payload['marketer_id'] = marketer.id
                print(f"   Assigning marketer: {marketer.email}")
            else:
                print(f"   ⚠️  No marketer found in this company - skipping client assignment")
                continue
        
        # Create mock request with JSON body
        import json as json_module
        request = factory.post(
            '/api/add-existing-user-to-company/',
            data=json_module.dumps(payload),
            content_type='application/json'
        )
        request.user = admin
        
        try:
            response = add_existing_user_to_company(request)
            data = json.loads(response.content)
            
            if 'error' in data:
                print(f"   ❌ API ERROR: {data['error']}")
                if 'existing' in data:
                    print(f"      (User already in company)")
            elif 'success' in data and data['success']:
                print(f"   ✅ User added successfully!")
                print(f"      Message: {data.get('message', '')}")
            else:
                print(f"   ❓ Unexpected response: {data}")
        except Exception as e:
            import traceback
            print(f"   ❌ EXCEPTION: {str(e)}")
            traceback.print_exc()


def check_company_profile_linkage():
    """Check if company_profile foreign key is properly set up"""
    print_section("STEP 5: COMPANY PROFILE LINKAGE CHECK")
    
    companies = Company.objects.all()
    
    print(f"\n📊 Total Companies: {companies.count()}\n")
    
    for company in companies:
        print(f"Company: {company.company_name} (ID: {company.id})")
        
        # Count users with this profile
        users = CustomUser.objects.filter(company_profile=company)
        print(f"  Users: {users.count()}")
        
        # Count admins
        admins = users.filter(role='admin')
        print(f"  Admins: {admins.count()}")
        
        if admins:
            for admin in admins:
                print(f"    - {admin.email}")


def main():
    """Run all diagnostics"""
    print("\n")
    print("█" * 80)
    print("█  MULTI-COMPANY ADD-EXISTING-USER DIAGNOSTIC")
    print("█  Diagnosing: 'IT ADDS FOR COMPANY A BUT NOT ADDING FOR COMPANY B'")
    print("█" * 80)
    
    try:
        diagnose_companies()
        diagnose_users()
        check_company_profile_linkage()
        test_search_isolation()
        test_add_isolation()
        
        print_section("DIAGNOSTIC COMPLETE")
        print("\n✅ Check output above for any ❌ errors or ⚠️  warnings\n")
        
    except Exception as e:
        import traceback
        print(f"\n❌ FATAL ERROR: {str(e)}")
        traceback.print_exc()


if __name__ == '__main__':
    main()
