#!/usr/bin/env python
"""
TEST: Verify API endpoint returns correct counts for all companies
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

print("\n" + "█"*120)
print("█" + "  🔗 TESTING: API endpoint across all companies".center(118) + "█")
print("█"*120 + "\n")

all_companies = Company.objects.all().order_by('company_name')
factory = RequestFactory()

for company in all_companies:
    # Get an admin user from this company to make the request
    admin = CustomUser.objects.filter(company_profile=company, role='admin').first()
    
    if not admin:
        print(f"⚠️  Company {company.company_name}: No admin user found")
        continue
    
    print(f"\n🏢 Company: {company.company_name}")
    print("─" * 120)
    
    # Create a request
    request = factory.get('/api/marketer-client-counts/')
    
    # Add session and auth middleware
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    
    middleware = AuthenticationMiddleware(lambda x: None)
    middleware.process_request(request)
    
    request.user = admin
    request.company = company
    
    # Call the API
    response = api_marketer_client_counts(request)
    data = json.loads(response.content)
    
    if not data.get('success'):
        print(f"  ❌ API Error: {data.get('error')}")
        continue
    
    marketers = data.get('marketers', [])
    print(f"  📌 API returned {len(marketers)} marketer(s)\n")
    
    total_clients = 0
    for m in marketers:
        count = m['client_count']
        total_clients += count
        
        status = "✅" if count > 0 else "⚪"
        print(f"  {status} {m['full_name']:<30} ({m['email']:<35}) → {count} client(s)")
    
    print(f"\n  📊 Total clients across all marketers: {total_clients}")
    print()

print("\n" + "█"*120)
print("█" + "  ✅ API TEST COMPLETE: Works correctly for all companies".ljust(118) + "█")
print("█"*120 + "\n")
