#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, 'c:/Users/HP/Documents/VictorGodwin/RE/Multi-Tenant Architecture/RealEstateMSApp/estateProject')
django.setup()

from estateApp.models import MarketerAffiliation, Company, CustomUser

# Quick test to verify the import works
try:
    company = Company.objects.get(company_name='Lamba Real Homes')
    affiliation_marketers = MarketerAffiliation.objects.filter(company=company).count()
    print(f'✅ MarketerAffiliation import works!')
    print(f'✅ Found {affiliation_marketers} affiliated marketers in {company.company_name}')
    print(f'✅ Fix is working correctly!')
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
