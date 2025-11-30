#!/usr/bin/env python
"""
Check admin user details
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from estateApp.models import Company, CustomUser

company = Company.objects.filter(company_name='Lamba Real Homes').first()
admin = CustomUser.objects.filter(company_profile=company, role='admin').first()

print(f"Admin: {admin.email}")
print(f"Password hash: {admin.password[:50]}")
print(f"Is staff: {admin.is_staff}")
print(f"Is superuser: {admin.is_superuser}")
