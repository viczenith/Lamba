import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
import django
django.setup()

from estateApp.models import AdminUser, Company

company = Company.objects.filter(company_name__icontains='lamba').first()
print('Company:', company)
print('Company ID:', company.id if company else None)

master_admin = AdminUser.objects.filter(company_profile=company).order_by('date_joined').first()
print('Master Admin:', master_admin.email if master_admin else None)
print('Master Admin ID:', master_admin.id if master_admin else None)

# Check all admins
print('\nAll Admins:')
admins = AdminUser.objects.filter(company_profile=company)
for a in admins:
    is_master = a.id == master_admin.id if master_admin else False
    has_fc = getattr(a, 'has_full_control', False)
    print(f'  Admin {a.id}: {a.email}')
    print(f'    has_full_control: {has_fc}')
    print(f'    is_master: {is_master}')
    print(f'    Should skip password modal: {is_master or has_fc}')
    print()
