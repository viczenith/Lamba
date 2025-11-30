"""
Clean all clients and marketers for Lamba Property Limited (LAMBA REAL HOMES), including affiliations.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company, ClientUser, MarketerUser, MarketerAffiliation, ClientMarketerAssignment

COMPANY_SLUG = 'lamba-property-limited'
company = Company.objects.get(slug=COMPANY_SLUG)

# Delete all client-marketer assignments for this company
ClientMarketerAssignment.objects.filter(company=company).delete()
print('✓ Deleted all ClientMarketerAssignment for Lamba')

# Delete all marketer affiliations for this company
MarketerAffiliation.objects.filter(company=company).delete()
print('✓ Deleted all MarketerAffiliation for Lamba')

# Delete all clients for this company
ClientUser.objects.filter(company_profile=company).delete()
print('✓ Deleted all ClientUser for Lamba')

# Delete all marketers for this company
MarketerUser.objects.filter(company_profile=company).delete()
print('✓ Deleted all MarketerUser for Lamba')

print('All clients, marketers, and affiliations for Lamba Property Limited have been cleaned.')
