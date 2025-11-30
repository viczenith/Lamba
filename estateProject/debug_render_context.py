#!/usr/bin/env python
"""
Debug: Check if marketer select is properly rendering in test context
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
from estateApp.models import Company, CustomUser
import re

company = Company.objects.filter(company_name='Lamba Real Homes').first()
admin = CustomUser.objects.filter(company_profile=company, role='admin').first()

factory = RequestFactory()
request = factory.get(f'/user-registration/?company={company.slug}')

middleware = SessionMiddleware(lambda x: None)
middleware.process_request(request)
request.session.save()

middleware = AuthenticationMiddleware(lambda x: None)
middleware.process_request(request)

request.user = admin
request.company = company

# Debug the context passed to template
print("Checking view response and marketers...\n")

response = user_registration(request)

# Check the context
if hasattr(response, 'context_data'):
    print(f"Context data available")
    marketers = response.context_data.get('marketers')
    print(f"Marketers in context: {marketers}")
    print(f"Marketer count: {marketers.count() if hasattr(marketers, 'count') else len(marketers)}")
elif hasattr(response, 'context'):
    print(f"Context available (direct)")
    context = response.context
    if isinstance(context, list):
        for ctx in context:
            if 'marketers' in ctx:
                marketers = ctx['marketers']
                print(f"Marketers in context: {marketers}")
                print(f"Marketer count: {marketers.count() if hasattr(marketers, 'count') else len(marketers)}")

# Get HTML and search for marketer options
html = response.rendered_content.decode('utf-8') if hasattr(response, 'rendered_content') else response.content.decode('utf-8')

# Find select tag
select_pattern = r'<select[^>]*id=["\']marketer["\'][^>]*>'
select_match = re.search(select_pattern, html)

if select_match:
    idx = select_match.start()
    snippet = html[idx:idx+1000]
    print(f"\nHTML snippet around marketer select:")
    print(snippet[:500])
    print("\n...")
