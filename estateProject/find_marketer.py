#!/usr/bin/env python
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.getcwd())
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from estateApp.views import user_registration
from estateApp.models import Company, CustomUser

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

response = user_registration(request)
html = response.content.decode('utf-8')

# Find marketer select and show context
import re
idx = html.find('id="marketer"')
print(f"Found 'id=\"marketer\"' at position {idx}")

if idx > 0:
    snippet = html[max(0, idx-200):idx+1000]
    print("\nContext around id=\"marketer\":")
    print(snippet)
