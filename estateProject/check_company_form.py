import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
root = os.path.dirname(os.path.abspath(__file__))
if root not in sys.path:
    sys.path.insert(0, root)

django.setup()

from estateApp.forms import CompanyForm
from estateApp.models import Company, CustomUser
from django.db import transaction

payload = {
    'company_name': 'TestCo_debug',
    'registration_number': 'RC99999',
    'registration_date': '2025-11-22',
    'location': 'Debug City',
    'ceo_name': 'Debug CEO',
    'ceo_dob': '1990-01-01',
    'email': f'debug+{os.getpid()}@example.com',
    'phone': '+10000000000',
}

print('\n== CompanyForm validation check ==')
form = CompanyForm(payload)
print('is_valid():', form.is_valid())
print('errors:', form.errors.as_json())

if form.is_valid():
    try:
        with transaction.atomic():
            company = form.save(commit=False)
            company.is_active = True
            company.subscription_status = 'trial'
            company.trial_ends_at = None
            company.api_calls_today = 0
            company.save()
            print('Saved company id:', company.id, 'slug:', company.slug)
    except Exception as e:
        print('Error saving company:', e)

# Check uniqueness constraints by trying duplicate
print('\n== Duplicate check ==')
if Company.objects.filter(registration_number=payload['registration_number']).exists():
    print('Duplicate registration_number exists')
else:
    print('No duplicate registration_number found')

print('\n== Existing company count ==')
print(Company.objects.count())

print('\n== CustomUser existing with email? ==')
print(CustomUser.objects.filter(email=payload['email']).exists())

print('\n== Done ==\n')
