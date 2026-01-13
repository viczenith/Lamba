#!/usr/bin/env python
"""
Script to create SuperAdmin user
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create or update superadmin user
user, created = User.objects.get_or_create(
    email='admin@system.com',
    defaults={
        'full_name': 'System Administrator',
        'first_name': 'System',
        'last_name': 'Administrator',
        'phone': '0000000000',
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
        'is_system_admin': True,
        'admin_level': 'system',
    }
)

# Update all fields to ensure they're set correctly
user.full_name = 'System Administrator'
user.first_name = 'System'
user.last_name = 'Administrator'
user.phone = '0000000000'
user.is_system_admin = True
user.admin_level = 'system'
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.role = 'admin'
user.set_password('AdminPass@2024')
user.save()

print('=' * 60)
print('SUPERADMIN USER CREATED SUCCESSFULLY!')
print('=' * 60)
print(f'Status: {"CREATED" if created else "UPDATED"}')
print(f'Email: {user.email}')
print(f'Full Name: {user.full_name}')
print(f'Password: AdminPass@2024')
print(f'Role: {user.role}')
print(f'Is System Admin: {user.is_system_admin}')
print(f'Admin Level: {user.admin_level}')
print(f'Is Superuser: {user.is_superuser}')
print(f'Is Staff: {user.is_staff}')
print(f'Is Active: {user.is_active}')
print('=' * 60)
print('LOGIN DETAILS:')
print('📧 Email:    admin@system.com')
print('🔑 Password: AdminPass@2024')
print('🌐 URL:      http://127.0.0.1:8000/super-admin/login/')
print('=' * 60)
