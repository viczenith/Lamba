"""
Debug script to test the check_full_control API response.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from estateApp.models import CustomUser, AdminUser, Company

print("=" * 60)
print("DEBUGGING check_full_control RESPONSE LOGIC")
print("=" * 60)

# Get test users
test_users = CustomUser.objects.filter(role='admin')

for user in test_users:
    print(f"\n--- Testing User: {user.email} (ID: {user.id}) ---")
    
    company = user.company_profile
    if not company:
        print(f"  Result: has_full_control=False, is_master=False (no company)")
        continue
    
    # Simulating the view logic
    master_admin = AdminUser.objects.filter(company_profile=company).order_by('date_joined').first()
    is_master = master_admin and user.id == master_admin.id
    has_full_control_attr = getattr(user, 'has_full_control', False)
    has_full_control = is_master or has_full_control_attr
    
    print(f"  Company: {company.company_name} (ID: {company.id})")
    print(f"  Master Admin ID: {master_admin.id if master_admin else 'None'}")
    print(f"  is_master: {is_master}")
    print(f"  has_full_control attribute: {has_full_control_attr}")
    print(f"  FINAL has_full_control: {has_full_control}")
    print(f"  API Response would be: {{'has_full_control': {has_full_control}, 'is_master': {is_master}}}")
    
    if has_full_control:
        print(f"  ✓ JavaScript will SHOW content directly (no password modal)")
    else:
        print(f"  ✗ JavaScript will SHOW password modal")

print("\n" + "=" * 60)
