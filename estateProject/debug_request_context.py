#!/usr/bin/env python
"""
Debug the exact request context
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

def test_request_context():
    """
    Check what happens in the view with our request
    """
    print("\n" + "="*100)
    print("DEBUG: Request context in view")
    print("="*100 + "\n")
    
    # Get company
    company = Company.objects.filter(company_name='Lamba Real Homes').first()
    print(f"Company: {company.company_name} (ID: {company.id})")
    
    # Get admin user
    admin = CustomUser.objects.filter(
        company_profile=company,
        role='admin'
    ).first()
    
    if not admin:
        admin = CustomUser.objects.filter(role='admin').first()
    
    print(f"Admin: {admin.full_name} (ID: {admin.id})")
    print(f"Admin company_profile: {admin.company_profile}")
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get(f'/user-registration/?company={company.slug}')
    
    # Add middleware
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    
    middleware = AuthenticationMiddleware(lambda x: None)
    middleware.process_request(request)
    
    # Set user
    request.user = admin
    
    # Check what gets set
    print(f"\nRequest attributes:")
    print(f"  request.user: {request.user}")
    print(f"  request.user.company_profile: {request.user.company_profile}")
    print(f"  hasattr(request, 'company'): {hasattr(request, 'company')}")
    if hasattr(request, 'company'):
        print(f"  request.company: {request.company}")
    else:
        print(f"  request.company: NOT SET")
    
    # Now manually trace what the view does
    print(f"\nView logic (first few lines):")
    company_from_view = getattr(request, 'company', None) or getattr(request.user, 'company_profile', None)
    print(f"  company = getattr(request, 'company', None) or getattr(request.user, 'company_profile', None)")
    print(f"  => company = {company_from_view}")
    
    # Check the get_all_marketers logic
    print(f"\nget_all_marketers() logic:")
    
    def get_all_marketers(company_obj):
        if not company_obj:
            print(f"    company_obj is None/empty, returning []")
            return []
        
        # Get marketers from company_profile
        marketers_primary = CustomUser.objects.filter(role='marketer', company_profile=company_obj)
        print(f"    marketers_primary count: {marketers_primary.count()}")
        
        # Get marketers from MarketerAffiliation
        marketers_affiliated = CustomUser.objects.none()
        try:
            affiliation_marketer_ids = MarketerAffiliation.objects.filter(
                company=company_obj
            ).values_list('marketer_id', flat=True).distinct()
            print(f"    affiliation_marketer_ids: {list(affiliation_marketer_ids)}")
            if affiliation_marketer_ids:
                marketers_affiliated = CustomUser.objects.filter(
                    id__in=affiliation_marketer_ids
                ).exclude(
                    id__in=marketers_primary.values_list('pk', flat=True)
                )
                print(f"    marketers_affiliated count: {marketers_affiliated.count()}")
        except Exception as e:
            print(f"    Exception: {e}")
            pass
        
        all_marketer_ids = set(marketers_primary.values_list('pk', flat=True)) | set(
            marketers_affiliated.values_list('pk', flat=True)
        )
        print(f"    all_marketer_ids: {all_marketer_ids}")
        result = CustomUser.objects.filter(id__in=all_marketer_ids).order_by('full_name')
        print(f"    final result count: {result.count()}")
        return result
    
    marketers = get_all_marketers(company_from_view)
    print(f"\nFinal marketers:")
    print(f"  Count: {marketers.count() if hasattr(marketers, 'count') else len(marketers)}")
    print(f"  Type: {type(marketers)}")

if __name__ == '__main__':
    test_request_context()
