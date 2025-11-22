"""
Create a simple test request to trigger the client view and see logs
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

# Get the admin user
admin_user = User.objects.filter(email='estate@gmail.com').first()

if not admin_user:
    print("❌ Admin user not found!")
    exit(1)

print(f"Testing with user: {admin_user.email}")
print(f"User has company_profile: {admin_user.company_profile is not None}")
if admin_user.company_profile:
    print(f"Company: {admin_user.company_profile.company_name}")
print()

# Create a test client and login
client = Client()
client.force_login(admin_user)

print("Making request to /client...")
print("=" * 60)
response = client.get('/client')
print("=" * 60)
print(f"Response status: {response.status_code}")
print(f"Response has clients context: {'clients' in response.context if response.context else 'No context'}")
if response.context and 'clients' in response.context:
    clients = response.context['clients']
    print(f"Clients count: {len(clients)}")
    for c in list(clients)[:3]:
        print(f"  - {c.email} ({c.full_name})")
else:
    print("⚠️ No clients in context!")
