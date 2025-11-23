import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root)
django.setup()

from estateApp.models import Company, CustomUser
import random
import string

rnd = lambda n=6: ''.join(random.choice(string.ascii_lowercase) for _ in range(n))

cn = f'TestCo_{rnd(4)}'
rn = f'RC{random.randint(10000,99999)}'
em = f'{rnd()}@example.com'

print('\n== PRE-CHECKS ==')
print(f'Check Company name: {Company.objects.filter(company_name=cn).exists()}')
print(f'Check Reg Number: {Company.objects.filter(registration_number=rn).exists()}')
print(f'Check Company email: {Company.objects.filter(email=em).exists()}')
print(f'Check CustomUser email: {CustomUser.objects.filter(email=em).exists()}')

print('\n== DIRECT COMPANY CREATE ==')
from django.utils import timezone
from datetime import timedelta

try:
    trial_end = timezone.now() + timedelta(days=14)
    company = Company.objects.create(
        company_name=cn,
        registration_number=rn,
        registration_date='2025-11-22',
        location='Test',
        ceo_name='CEO',
        ceo_dob='1990-01-01',
        email=em,
        phone='+1000',
        is_active=True,
        subscription_status='trial',
        trial_ends_at=trial_end,
        subscription_tier='starter'
    )
    print(f'✓ Created company: {company.id} - {company.company_name}')
    print(f'  - Slug: {company.slug}')
except Exception as e:
    print(f'✗ Error: {type(e).__name__}: {e}')

print('\n== DB CHECK ==')
print(f'Company exists now: {Company.objects.filter(company_name=cn).exists()}')
print('\n')
