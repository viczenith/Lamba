#!/usr/bin/env python
"""
Script to create a system admin user for Tenant Admin dashboard
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import CustomUser

# Create system admin user
try:
    user = CustomUser.objects.create_superuser(
        email='admin@system.com',
        full_name='System Administrator',
        phone='1234567890',
        password='SecurePassword@123'
    )
    user.is_system_admin = True
    user.admin_level = 'system'
    user.company_profile = None
    user.save()

    print(f"✅ System admin created successfully!")
    print(f"Email: {user.email}")
    print(f"Password: SecurePassword@123")
    print(f"is_system_admin: {user.is_system_admin}")
    print(f"admin_level: {user.admin_level}")
except Exception as e:
    print(f"Error creating admin user: {e}")
