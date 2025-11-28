#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from estateApp.models import CustomUser

# Check test user
user = CustomUser.objects.get(email='testclient@example.com')
print(f"User: {user.email}")
print(f"  ID: {user.id}")
print(f"  is_active: {user.is_active}")
print(f"  is_deleted: {user.is_deleted}")
print(f"  role: {user.role}")
print(f"  company_profile: {user.company_profile}")

# Try the exact query
try:
    found = CustomUser.objects.get(id=user.id, is_active=True, is_deleted=False)
    print(f"\n✅ Query succeeded: {found.email}")
except Exception as e:
    print(f"\n❌ Query failed: {str(e)}")
