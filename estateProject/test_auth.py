#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import CustomUser
from django.urls import reverse

print("✅ URL config and authentication test\n")

# Test URLs
try:
    print(f"Login URL: {reverse('login')}")
    print(f"Register URL: {reverse('register')}")
    print(f"Register User URL: {reverse('register-user')}")
    print(f"Admin Dashboard URL: {reverse('admin-dashboard')}")
    print(f"Client Dashboard URL: {reverse('client-dashboard')}")
    print(f"Marketer Dashboard URL: {reverse('marketer-dashboard')}")
except Exception as e:
    print(f"❌ URL Error: {e}")

print("\n--- User Information ---")
total = CustomUser.objects.count()
print(f"Total users: {total}")

# Check admin users
admins = CustomUser.objects.filter(role='admin')
print(f"\nAdmin users ({admins.count()}):")
for admin in admins:
    print(f"  - {admin.email}: admin_level={admin.admin_level}, company={admin.company}")

# Check client users
clients = CustomUser.objects.filter(role='client')
print(f"\nClient users ({clients.count()}):")
for client in clients[:5]:  # Show first 5
    print(f"  - {client.email}: admin_level={client.admin_level}")

# Check marketer users
marketers = CustomUser.objects.filter(role='marketer')
print(f"\nMarketer users ({marketers.count()}):")
for marketer in marketers[:5]:  # Show first 5
    print(f"  - {marketer.email}: admin_level={marketer.admin_level}")

print("\n✅ Test completed")
