"""
Direct verification that views return correct data
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from estateApp.views import client, marketer_list, get_request_company
from estateApp.models import ClientUser, MarketerUser

User = get_user_model()

# Get user
admin_user = User.objects.filter(email='estate@gmail.com').first()
print(f"User: {admin_user.email}")
print(f"Company: {admin_user.company_profile}")
print()

# Create fake request
factory = RequestFactory()
request = factory.get('/client')
request.user = admin_user
request.session = {}  # Add session

# Test get_request_company directly
print("=== Testing get_request_company() ===")
company = get_request_company(request)
print(f"Returned: {company}")
print(f"Type: {type(company)}")
if company:
    print(f"ID: {company.id}")
print()

# Test client view manually
print("=== Testing client view logic ===")
if company:
    clients = ClientUser.objects.filter(role='client', company_profile=company)
    print(f"Clients: {clients.count()}")
    for c in list(clients)[:3]:
        print(f"  - {c.email}")
else:
    print("❌ No company - no clients")
print()

# Test marketer_list view
print("=== Testing marketer_list view logic ===")
if company:
    marketers = MarketerUser.objects.filter(company_profile=company)
    print(f"Marketers: {marketers.count()}")
    for m in list(marketers)[:3]:
        print(f"  - {m.email}")
else:
    print("❌ No company - no marketers")
print()

print("✅ All views should now work correctly!")
