#!/usr/bin/env python
"""
Debug: Print the exact QuerySet being passed to the template
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
from estateApp.models import Company, CustomUser, MarketerAffiliation
from django.http import HttpResponse
from django.template import Template, Context

def test_view_logic():
    """
    Test the exact logic from the view
    """
    print("\n" + "="*100)
    print("DEBUG: Testing view logic for get_all_marketers")
    print("="*100 + "\n")
    
    # Get company
    company = Company.objects.filter(company_name='Lamba Real Homes').first()
    print(f"Company: {company}\n")
    
    # Replicate the helper function
    def get_all_marketers(company_obj):
        """Fetch marketers from both company_profile and MarketerAffiliation"""
        if not company_obj:
            return []
        
        # Get marketers from company_profile
        marketers_primary = CustomUser.objects.filter(role='marketer', company_profile=company_obj)
        
        # Get marketers from MarketerAffiliation (for users added via add_existing_user_to_company)
        marketers_affiliated = CustomUser.objects.none()
        try:
            affiliation_marketer_ids = MarketerAffiliation.objects.filter(
                company=company_obj
            ).values_list('marketer_id', flat=True).distinct()
            if affiliation_marketer_ids:
                marketers_affiliated = CustomUser.objects.filter(
                    id__in=affiliation_marketer_ids
                ).exclude(
                    id__in=marketers_primary.values_list('pk', flat=True)
                )
        except Exception as e:
            print(f"Exception: {e}")
            pass
        
        # Combine using Q object to ensure proper QuerySet union
        all_marketer_ids = set(marketers_primary.values_list('pk', flat=True)) | set(
            marketers_affiliated.values_list('pk', flat=True)
        )
        print(f"All marketer IDs: {all_marketer_ids}")
        
        # Return a single QuerySet with all marketers
        result = CustomUser.objects.filter(id__in=all_marketer_ids).order_by('full_name')
        print(f"Result QuerySet: {result}")
        print(f"Result count: {result.count()}")
        print(f"Result list: {list(result)}")
        return result
    
    # Get all marketers for the company
    marketers = get_all_marketers(company)
    
    print(f"\nFinal marketers variable:")
    print(f"  Type: {type(marketers)}")
    print(f"  Value: {marketers}")
    
    # Try to iterate
    print(f"\nIteration test:")
    for i, m in enumerate(marketers):
        print(f"  {i}: {m.id} - {m.full_name}")
    
    # Test in Django template
    print(f"\nTemplate rendering test:")
    template_str = "{% for marketer in marketers %}<option value=\"{{ marketer.id }}\">{{ marketer.full_name }}</option>{% endfor %}"
    template = Template(template_str)
    context = Context({'marketers': marketers})
    rendered = template.render(context)
    print(f"  Rendered HTML:\n{rendered}")

if __name__ == '__main__':
    test_view_logic()
