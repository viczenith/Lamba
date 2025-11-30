#!/usr/bin/env python
"""
Detailed debug of the exact flow
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
from django.template.loader import get_template
from django.template import Context

def test_template_directly():
    """
    Load the actual template and render it directly with marketers
    """
    print("\n" + "="*100)
    print("TEST: Direct template rendering with marketers")
    print("="*100 + "\n")
    
    # Get company and marketers
    company = Company.objects.filter(company_name='Lamba Real Homes').first()
    print(f"Company: {company}\n")
    
    # Get marketers using the same logic
    def get_all_marketers(company_obj):
        if not company_obj:
            return []
        
        marketers_primary = CustomUser.objects.filter(role='marketer', company_profile=company_obj)
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
        except Exception:
            pass
        
        all_marketer_ids = set(marketers_primary.values_list('pk', flat=True)) | set(
            marketers_affiliated.values_list('pk', flat=True)
        )
        return CustomUser.objects.filter(id__in=all_marketer_ids).order_by('full_name')
    
    marketers = get_all_marketers(company)
    print(f"Marketers QuerySet:")
    print(f"  Count: {marketers.count()}")
    print(f"  Type: {type(marketers)}")
    for m in marketers:
        print(f"    - {m.id}: {m.full_name}")
    
    # Load and render the actual template
    print(f"\nLoading template: admin_side/user_registration.html")
    try:
        template = get_template('admin_side/user_registration.html')
        print(f"✅ Template loaded")
    except Exception as e:
        print(f"❌ Error loading template: {e}")
        return
    
    # Create context
    context = {'marketers': marketers}
    print(f"\nRendering template with context:")
    print(f"  marketers: {marketers}")
    
    try:
        html = template.render(context)
        print(f"✅ Template rendered ({len(html)} bytes)")
    except Exception as e:
        print(f"❌ Error rendering template: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Extract the dropdown
    import re
    select_pattern = r'<select[^>]*id=["\']marketer["\'][^>]*>(.*?)</select>'
    match = re.search(select_pattern, html, re.DOTALL)
    
    if match:
        select_content = match.group(1)
        option_pattern = r'<option[^>]*value=["\']([^"\']*)["\'][^>]*>([^<]*)</option>'
        options = re.findall(option_pattern, select_content)
        
        print(f"\n✅ Found marketer select with {len(options)} options:")
        for value, text in options:
            if value:
                print(f"    - ID={value}, Name={text}")
            else:
                print(f"    - [Default] {text}")
    else:
        print(f"\n❌ Could not find marketer select in HTML")

if __name__ == '__main__':
    test_template_directly()
