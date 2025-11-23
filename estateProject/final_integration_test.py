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

cn = f'FinalTest_{rnd(4)}'
em = f'{rnd()}@final.test'
pw = 'SecurePass@2025'

print('\n=== COMPANY REGISTRATION AND LOGIN TEST ===\n')

# 1. Register Company
print('1. Registering company...')
c = Client()
reg_resp = c.post('/register/', {
    'company_name': cn,
    'registration_number': f'RC{random.randint(10000,99999)}',
    'registration_date': '2025-11-22',
    'location': 'Final Test City',
    'ceo_name': 'Final Test CEO',
    'ceo_dob': '1990-01-01',
    'email': em,
    'phone': '+1234567890',
    'password': pw,
    'confirm_password': pw,
    'secondary_admin_email': f'{rnd()}@final.test',
    'secondary_admin_phone': '+9876543210',
    'secondary_admin_name': 'Final Test Admin',
})

print(f'   Registration status: {reg_resp.status_code}')
company = Company.objects.filter(company_name=cn).first()
admin = CustomUser.objects.filter(email=em).first()
print(f'   Company created: {company is not None}' + (f' (ID: {company.id}, slug: {company.slug})' if company else ''))
print(f'   Admin created: {admin is not None}' + (f' (ID: {admin.id}, role: {admin.role})' if admin else ''))

# 2. Try login with registered credentials
print('\n2. Attempting login with registered email/password...')
login_resp = c.post('/login/', {'username': em, 'password': pw}, follow=False)
print(f'   Login POST status: {login_resp.status_code}')

# Check if authentication succeeded
from django.contrib.auth import get_user
logged_in_user = get_user(c)
print(f'   Client authenticated: {logged_in_user.is_authenticated}')
if logged_in_user.is_authenticated:
    print(f'   Logged in as: {logged_in_user.email} (role: {logged_in_user.role})')

# 3. Summary
print('\n=== SUMMARY ===')
print(f'✓ Company registration: {company is not None}')
print(f'✓ Admin account creation: {admin is not None}')
print(f'✓ Login with registered credentials: {logged_in_user.is_authenticated}')
print('\n')
