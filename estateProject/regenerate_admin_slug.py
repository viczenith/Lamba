"""
Regenerate admin user slugs to use company name
"""
from estateApp.models import CustomUser

# Get all admin users
admins = CustomUser.objects.filter(role='admin')

for admin in admins:
    # Clear slug to trigger regeneration
    admin.slug = ''
    admin.save()
    company_name = admin.company_profile.name if admin.company_profile else 'No Company'
    print(f'{admin.full_name} ({admin.role}): /{admin.slug}/ (Company: {company_name})')

print(f'\n✅ Updated {admins.count()} admin users')
