#!/usr/bin/env python
"""
Final verification that the dropdown fix is complete
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

print("\n" + "="*100)
print("FINAL VERIFICATION: Marketer Dropdown Fix")
print("="*100 + "\n")

# Setup
company = Company.objects.filter(company_name='Lamba Real Homes').first()
admin = CustomUser.objects.filter(company_profile=company, role='admin').first()

if not company or not admin:
    print("❌ Setup failed")
    sys.exit(1)

print(f"✅ Company: {company.company_name}")
print(f"✅ Admin: {admin.full_name}\n")

# Create request
factory = RequestFactory()
request = factory.get(f'/user-registration/?company={company.slug}')

middleware = SessionMiddleware(lambda x: None)
middleware.process_request(request)
request.session.save()

middleware = AuthenticationMiddleware(lambda x: None)
middleware.process_request(request)

request.user = admin
request.company = company

# Get response
response = user_registration(request)
html = response.rendered_content.decode('utf-8') if hasattr(response, 'rendered_content') else response.content.decode('utf-8')

# Extract options
select_pattern = r'<select[^>]*id=["\']marketer["\'][^>]*>(.*?)</select>'
match = re.search(select_pattern, html, re.DOTALL)

if not match:
    print("❌ Could not find marketer select")
    sys.exit(1)

option_pattern = r'<option[^>]*value=["\']([^"\']*)["\'][^>]*>([^<]*)</option>'
options = re.findall(option_pattern, match.group(1))

# Verify
print(f"📊 Dropdown Content:")
print(f"   Total options: {len(options)}\n")

has_all_format = True
for value, text in options[1:]:  # Skip default
    print(f"   ✓ {text}")
    if '•' not in text or text.count('•') < 2:
        has_all_format = False

print()

checks = [
    ("Dropdown visible", len(options) > 0),
    ("All 4 marketers shown", len(options) == 5),  # 4 + 1 default
    ("Format includes email", all('•' in options[i][1] for i in range(1, len(options)))),
    ("Format includes client count", all('client' in options[i][1] for i in range(1, len(options)))),
]

all_pass = True
for check_name, result in checks:
    status = "✅" if result else "❌"
    print(f"{status} {check_name}")
    if not result:
        all_pass = False

print("\n" + "="*100)
if all_pass:
    print("✅ ALL CHECKS PASSED - DROPDOWN FIX VERIFIED")
else:
    print("❌ SOME CHECKS FAILED")
print("="*100 + "\n")

sys.exit(0 if all_pass else 1)
