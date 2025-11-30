#!/usr/bin/env python
"""
Test API endpoint after fix
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.getcwd())
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from estateApp.views import api_marketer_client_counts
from estateApp.models import Company, CustomUser
import json

print("\n" + "="*100)
print("TEST: API Endpoint with Fixed Client Count")
print("="*100 + "\n")

company = Company.objects.filter(company_name='Lamba Real Homes').first()
admin = CustomUser.objects.filter(company_profile=company, role='admin').first()

factory = RequestFactory()
request = factory.get('/api/marketer-client-counts/')

middleware = SessionMiddleware(lambda x: None)
middleware.process_request(request)
request.session.save()

middleware = AuthenticationMiddleware(lambda x: None)
middleware.process_request(request)

request.user = admin
request.company = company

response = api_marketer_client_counts(request)
data = json.loads(response.content.decode('utf-8'))

print("API Response:")
print(json.dumps(data, indent=2))

print("\n" + "="*100)
print("Marketer Client Counts:")
print("="*100 + "\n")

for m in data['marketers']:
    plural = "client" if m['client_count'] == 1 else "clients"
    status = "✅" if m['client_count'] > 0 else "⚠️"
    print(f"{status} {m['full_name']} ({m['email']}) → {m['client_count']} {plural}")

print()
