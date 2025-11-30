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
html = response.rendered_content.decode('utf-8') if hasattr(response, 'rendered_content') else response.content.decode('utf-8')

# Count option tags
count = html.count('<option value="') - 1  # Subtract the default option
print(f'Marketers rendering: {count}')

# Show sample - check inside marketer select specifically
import re
select_match = re.search(r'id="marketer"[^>]*>(.*?)</select>', html, re.DOTALL)
if select_match:
    select_html = select_match.group(1)
    marketer_count = len(re.findall(r'<option value="(\d+)"', select_html))
    print(f'\nMarketer options inside select: {marketer_count}')
    
    if '<option value="15"' in select_html:
        print("✅ Marketer 15 found")
    if '<option value="8"' in select_html:
        print("✅ Marketer 8 found")
    if '<option value="89"' in select_html:
        print("✅ Marketer 89 found")
    if '<option value="107"' in select_html:
        print("✅ Marketer 107 found")

    if marketer_count == 4:
        print("\n✅ ALL 4 MARKETERS ARE RENDERING!")
    else:
        print(f"\n⚠️ Found {marketer_count} marketers")
