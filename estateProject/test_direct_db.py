#!/usr/bin/env python
"""
Direct database test of add_existing_user_to_company logic without HTTP layer
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from estateApp.models import Company, CustomUser, MarketerUser, ClientUser
from django.db import transaction

print("\n" + "█"*80)
print("█  DIRECT DATABASE TEST: Add Existing User")
print("█"*80 + "\n")

# Get test data
lpl = Company.objects.get(company_name='Lamba Property Limited')
lrh = Company.objects.get(company_name='Lamba Real Homes')
admin_a = CustomUser.objects.filter(company_profile=lpl, role='admin').first()
admin_b = CustomUser.objects.filter(company_profile=lrh, role='admin').first()
test_user = CustomUser.objects.get(email='testclient@example.com')
marketer_a = MarketerUser.objects.filter(company_profile=lpl).first()

print(f"Test Setup:")
print(f"  Company A: {lpl.company_name} (ID: {lpl.id})")
print(f"  Company B: {lrh.company_name} (ID: {lrh.id})")
print(f"  Admin A: {admin_a.email}")
print(f"  Admin B: {admin_b.email}")
print(f"  Test User: {test_user.email} (ID: {test_user.id}, role: {test_user.role})")
print(f"  Marketer A: {marketer_a.email} (ID: {marketer_a.id})\n")

# TEST 1: Manually execute the logic that should happen in add_existing_user_to_company
print("="*80)
print("TEST 1: Add test user to Company A")
print("="*80 + "\n")

try:
    with transaction.atomic():
        print("Step 1: Get user")
        user = CustomUser.objects.get(id=test_user.id, is_active=True, is_deleted=False)
        print(f"  ✅ User found: {user.email}")
        
        print("\nStep 2: Check if user already in company")
        if user.company_profile and user.company_profile.id == lpl.id:
            print(f"  ❌ User already in {lpl.company_name}")
        else:
            print(f"  ✅ User not in {lpl.company_name}, can proceed")
        
        print("\nStep 3: Create ClientUser subclass")
        if not ClientUser.objects.filter(pk=user.id).exists():
            print(f"  ClientUser doesn't exist yet, creating...")
            # Try direct database insert
            from django.db import connection
            with connection.cursor() as cursor:
                # Get the structure first
                cursor.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name='estateapp_clientuser'"
                )
                schema = cursor.fetchone()
                if schema:
                    print(f"  Schema: {schema[0][:100]}...")
                
                # Try insert
                try:
                    cursor.execute(
                        "INSERT INTO estateapp_clientuser (customuser_ptr_id) VALUES (?)",
                        [user.id]
                    )
                    print(f"  ✅ ClientUser created via raw SQL")
                except Exception as e:
                    print(f"  ❌ Raw SQL insert failed: {str(e)}")
        else:
            print(f"  ✅ ClientUser already exists")
        
        print("\nStep 4: Get ClientUser instance")
        client_obj = ClientUser.objects.get(pk=user.id)
        print(f"  ✅ ClientUser retrieved: {client_obj.email}")
        
        print("\nStep 5: Assign marketer")
        client_obj.assigned_marketer = marketer_a
        client_obj.save()
        print(f"  ✅ Marketer assigned: {marketer_a.email}")
        
        print("\nStep 6: Add user to company")
        if not user.company_profile:
            user.company_profile = lpl
            user.save()
            print(f"  ✅ User.company_profile set to {lpl.company_name}")
        else:
            print(f"  ℹ️  User already had company_profile: {user.company_profile.company_name}")
        
        print("\n✅ TEST 1 SUCCESS")
        
except Exception as e:
    import traceback
    print(f"\n❌ TEST 1 FAILED: {str(e)}")
    traceback.print_exc()

# Reset user
print("\n\n" + "-"*80)
print("RESETTING TEST USER...")
test_user.company_profile = None
test_user.save()
print("-"*80 + "\n")

# TEST 2: Add to Company B
print("="*80)
print("TEST 2: Add test user to Company B")
print("="*80 + "\n")

try:
    with transaction.atomic():
        print("Step 1: Get user")
        user = CustomUser.objects.get(id=test_user.id, is_active=True, is_deleted=False)
        print(f"  ✅ User found: {user.email}")
        
        print("\nStep 2: Check if user already in company")
        if user.company_profile and user.company_profile.id == lrh.id:
            print(f"  ❌ User already in {lrh.company_name}")
        else:
            print(f"  ✅ User not in {lrh.company_name}, can proceed")
        
        print("\nStep 3: Create ClientUser subclass")
        if not ClientUser.objects.filter(pk=user.id).exists():
            print(f"  ClientUser doesn't exist yet, creating...")
            from django.db import connection
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        "INSERT INTO estateapp_clientuser (customuser_ptr_id) VALUES (?)",
                        [user.id]
                    )
                    print(f"  ✅ ClientUser created via raw SQL")
                except Exception as e:
                    print(f"  ❌ Raw SQL insert failed: {str(e)}")
        else:
            print(f"  ✅ ClientUser already exists")
        
        print("\nStep 4: Get ClientUser instance")
        client_obj = ClientUser.objects.get(pk=user.id)
        print(f"  ✅ ClientUser retrieved: {client_obj.email}")
        
        print("\nStep 5: Assign marketer")
        client_obj.assigned_marketer = marketer_a
        client_obj.save()
        print(f"  ✅ Marketer assigned: {marketer_a.email}")
        
        print("\nStep 6: Add user to company")
        if not user.company_profile:
            user.company_profile = lrh
            user.save()
            print(f"  ✅ User.company_profile set to {lrh.company_name}")
        else:
            print(f"  ℹ️  User already had company_profile: {user.company_profile.company_name}")
        
        print("\n✅ TEST 2 SUCCESS")
        
except Exception as e:
    import traceback
    print(f"\n❌ TEST 2 FAILED: {str(e)}")
    traceback.print_exc()

# Verify final state
print("\n\n" + "="*80)
print("FINAL STATE")
print("="*80 + "\n")

test_user.refresh_from_db()
print(f"Test user company_profile: {test_user.company_profile}")
if test_user.company_profile:
    print(f"  Company: {test_user.company_profile.company_name}")

in_lpl = ClientUser.objects.filter(id=test_user.id, company_profile=lpl).exists()
in_lrh = ClientUser.objects.filter(id=test_user.id, company_profile=lrh).exists()
print(f"\nClientUser in Company A: {'✅ YES' if in_lpl else '❌ NO'}")
print(f"ClientUser in Company B: {'✅ YES' if in_lrh else '❌ NO'}")

print("\n" + "█"*80)
print("█  TEST COMPLETE")
print("█"*80 + "\n")
