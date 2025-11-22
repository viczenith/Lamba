import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import MarketerUser, Company

company = Company.objects.filter(company_name='Lamba Real Homes').first()
print(f'Company: {company}')
print(f'\nMarketers in {company}:')

marketers = MarketerUser.objects.filter(company_profile=company)
print(f'Total count: {marketers.count()}')

for m in marketers:
    print(f'  - {m.full_name} ({m.email}) [ID: {m.pk}]')
