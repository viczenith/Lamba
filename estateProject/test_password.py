#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import CustomUser, Company

def test_password_verification():
    # Check if there are any admin users
    admins = CustomUser.objects.filter(role='admin')
    print(f'Found {admins.count()} admin users')

    if admins.exists():
        master_admin = admins.order_by('date_joined').first()
        print(f'Master admin: {master_admin.full_name} ({master_admin.email})')
        print(f'Company: {master_admin.company_profile.company_name if master_admin.company_profile else "No company"}')

        # Test password check with a known invalid password
        test_password = 'test123'  # This should fail
        is_valid = master_admin.check_password(test_password)
        print(f'Password "test123" valid: {is_valid}')

        # Test with empty password
        is_valid_empty = master_admin.check_password('')
        print(f'Empty password valid: {is_valid_empty}')
    else:
        print('No admin users found')

if __name__ == '__main__':
    test_password_verification()