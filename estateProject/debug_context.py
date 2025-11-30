#!/usr/bin/env python
"""
Debug: Check what's actually in the context passed to the template
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from estateApp.views import user_registration
from estateApp.models import Company, CustomUser, MarketerAffiliation

def debug_context():
    """
    Check what the view is actually computing
    """
    print("\n" + "="*100)
    print("DEBUG: Context Data in user_registration view")
    print("="*100 + "\n")
    
    # Get company
    company = Company.objects.filter(company_name='Lamba Real Homes').first()
    if not company:
        print("❌ Company not found")
        return
    
    print(f"Company: {company.company_name}\n")
    
    # Simulate exactly what the view does
    print("Step 1: Get marketers_primary")
    company_filter = {'company_profile': company}
    marketers_primary = CustomUser.objects.filter(role='marketer', **company_filter)
    print(f"  Query: CustomUser.objects.filter(role='marketer', company_profile={company.company_name})")
    print(f"  Count: {marketers_primary.count()}")
    print(f"  SQL: {marketers_primary.query}")
    for m in marketers_primary:
        print(f"    - {m.id}: {m.full_name} ({m.email})")
    
    print(f"\nStep 2: Get marketers_affiliated")
    marketers_affiliated = []
    try:
        affiliation_marketer_ids = MarketerAffiliation.objects.filter(
            company=company
        ).values_list('marketer_id', flat=True).distinct()
        print(f"  Affiliated IDs: {list(affiliation_marketer_ids)}")
        
        if affiliation_marketer_ids:
            marketers_affiliated = CustomUser.objects.filter(
                id__in=affiliation_marketer_ids
            ).exclude(
                id__in=marketers_primary.values_list('pk', flat=True)
            )
            print(f"  Count (after excluding primary): {marketers_affiliated.count()}")
            for m in marketers_affiliated:
                print(f"    - {m.id}: {m.full_name} ({m.email})")
    except Exception as e:
        print(f"  Error: {e}")
    
    print(f"\nStep 3: Combine into list")
    marketers = list(marketers_primary) + list(marketers_affiliated)
    print(f"  Type: {type(marketers)}")
    print(f"  Length: {len(marketers)}")
    print(f"  Contents: {marketers}")
    
    for i, m in enumerate(marketers):
        print(f"    {i}: {m.id} - {m.full_name} - {type(m)}")
    
    print(f"\nStep 4: Check template evaluation")
    print(f"  bool(marketers): {bool(marketers)}")
    print(f"  len(marketers): {len(marketers)}")
    print(f"  for loop would iterate: {len(marketers)} times")
    
    # Try to simulate Django template evaluation
    print(f"\nStep 5: Template loop simulation")
    template_output = []
    for marketer in marketers:
        print(f"  Iteration: marketer={marketer}, marketer.id={marketer.id}, marketer.full_name={marketer.full_name}")
        template_output.append(f'<option value="{marketer.id}">{marketer.full_name}</option>')
    
    print(f"\nGenerated HTML:")
    for opt in template_output:
        print(f"  {opt}")

if __name__ == '__main__':
    debug_context()
