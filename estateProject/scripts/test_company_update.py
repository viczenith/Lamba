import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import Client
from estateApp.models import CustomUser

print('Starting local POST test to /company-profile/update/')
admin = CustomUser.objects.filter(role='admin', company_profile__isnull=False).first()
company = None
if not admin:
    # Try to find any company and create a temporary admin for testing
    from estateApp.models import Company
    company = Company.objects.first()
    if not company:
        print('No companies found in DB. Aborting test.')
        raise SystemExit(1)

    print('No linked admin found; creating temporary admin for company:', company.company_name)
    admin = CustomUser.objects.create_user(
        email='devtest+admin@example.com',
        full_name='Dev Test Admin',
        phone='0000000000',
        password='testpass',
        role='admin',
        company_profile=company,
        is_staff=True,
        is_superuser=True
    )
else:
    company = admin.company_profile

client = Client()
client.force_login(admin)

# Prepare payload using existing company values; omit legacy ceo fields to test preservation
payload = {
    'company_name': company.company_name,
    'registration_number': company.registration_number,
    'registration_date': company.registration_date.isoformat(),
    'location': company.location,
    'email': company.email,
    'phone': company.phone,
    'is_active': 'on',
}

resp = client.post('/company-profile/update/', payload)
print('Response status:', resp.status_code)
try:
    print('Response JSON:', resp.json())
except Exception:
    print('Response content:', resp.content.decode('utf-8')[:2000])

# Verify Company still has ceo_name and ceo_dob intact
company.refresh_from_db()
print('Post-check company.ceo_name:', repr(company.ceo_name))
print('Post-check company.ceo_dob :', repr(company.ceo_dob))
print('Test complete.')
