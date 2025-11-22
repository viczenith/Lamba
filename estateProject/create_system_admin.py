#!/usr/bin/env python
"""Create system administrator user for tenant admin dashboard"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import CustomUser

# Create system administrator
try:
    admin = CustomUser.objects.get(email='admin@system.com')
    print(f"⚠️  System admin already exists: {admin.email}")
except CustomUser.DoesNotExist:
    admin = CustomUser.objects.create_superuser(
        email='admin@system.com',
        full_name='System Administrator',
        phone='1234567890',
        password='AdminPass@2024'
    )
    admin.is_system_admin = True
    admin.admin_level = 'system'
    admin.company_profile = None
    admin.save()
    print(f"✅ System Admin created successfully!")
    print(f"   Email: {admin.email}")
    print(f"   Password: AdminPass@2024")
    print(f"   Login URL: http://127.0.0.1:8000/tenant-admin/login/")
