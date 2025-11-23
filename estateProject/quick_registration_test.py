import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root)
django.setup()

from django.test import Client
from estateApp.models import Company, CustomUser
import random
import string

rnd = lambda n=6: ''.join(random.choice(string.ascii_lowercase) for _ in range(n))

cn = f'TestCo_{rnd(4)}'
em = f'{rnd()}@example.com'
pw = 'TestPass@123'

print('\n== Registration Test ==')
print(f'Company: {cn}')
print(f'Admin email: {em}')

c = Client()
resp = c.post('/register/', {
    'company_name': cn,
    'registration_number': f'RC{random.randint(10000,99999)}',
    'registration_date': '2025-11-22',
    'location': 'Test City',
    'ceo_name': 'Test CEO',
    'ceo_dob': '1990-01-01',
    'email': em,
    'phone': '+1234567890',
    'password': pw,
    'confirm_password': pw,
    'secondary_admin_email': f'{rnd()}@example.com',
    'secondary_admin_phone': '+9876543210',
    'secondary_admin_name': 'Secondary Admin',
})  # Do NOT follow redirects

print(f'Response status: {resp.status_code}')

# Capture response messages if available
if hasattr(resp, 'context') and resp.context:
    for msg in resp.context.get('messages', []):
        print(f'Message: {msg.tags} - {msg}')
else:
    print('No context messages available')

# Check database
company_created = Company.objects.filter(company_name=cn).exists()
admin_created = CustomUser.objects.filter(email=em).exists()

print(f'Company created in DB: {company_created}')
print(f'Admin user created in DB: {admin_created}')

if company_created:
    comp = Company.objects.get(company_name=cn)
    print(f'  - Company ID: {comp.id}')
    print(f'  - Company slug: {comp.slug}')
    print(f'  - Subscription status: {comp.subscription_status}')

if admin_created:
    admin = CustomUser.objects.get(email=em)
    print(f'  - Admin ID: {admin.id}')
    print(f'  - Admin role: {admin.role}')
    print(f'  - Admin level: {admin.admin_level}')
    print(f'  - Company profile: {admin.company_profile}')

print('\n== Test Complete ==\n')
