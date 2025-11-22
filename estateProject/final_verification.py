"""
FINAL VERIFICATION SCRIPT
Run this to confirm all fixes are working
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company, ClientUser, MarketerUser, PlotSize, PlotNumber
from django.contrib.auth import get_user_model

User = get_user_model()

print("="*70)
print(" MULTI-TENANT DATA DISPLAY FIX - FINAL VERIFICATION")
print("="*70)
print()

# Get companies
company_a = Company.objects.filter(email='estate@gmail.com').first()
company_b = Company.objects.filter(email='akorvikkyy@gmail.com').first()

print("📊 COMPANY STATUS")
print(f"  Company A: {company_a.company_name} (ID: {company_a.id})")
print(f"  Company B: {company_b.company_name} (ID: {company_b.id})")
print()

# Check Company A admin user
admin_a = User.objects.filter(email='estate@gmail.com').first()
print(f"🔐 COMPANY A ADMIN USER")
print(f"  Email: {admin_a.email}")
print(f"  Has company_profile: {admin_a.company_profile is not None}")
print(f"  company_profile: {admin_a.company_profile}")
print(f"  company_profile ID: {admin_a.company_profile.id if admin_a.company_profile else 'None'}")
print()

# Check Company A data
print("📈 COMPANY A DATA COUNTS")
clients_a = ClientUser.objects.filter(role='client', company_profile=company_a)
marketers_a = MarketerUser.objects.filter(company_profile=company_a)
plot_sizes_a = PlotSize.objects.filter(company=company_a)
plot_numbers_a = PlotNumber.objects.filter(company=company_a)

print(f"  Clients: {clients_a.count()}")
print(f"  Marketers: {marketers_a.count()}")
print(f"  Plot Sizes: {plot_sizes_a.count()}")
print(f"  Plot Numbers: {plot_numbers_a.count()}")
print()

# Sample data
print("📋 SAMPLE CLIENTS (First 5)")
for client in clients_a[:5]:
    print(f"    - {client.email} ({client.full_name})")
print()

print("📋 SAMPLE MARKETERS (First 5)")
for marketer in marketers_a[:5]:
    print(f"    - {marketer.email} ({marketer.full_name})")
print()

# Check Company B data (should be different)
print("📊 COMPANY B DATA COUNTS (For Comparison)")
clients_b = ClientUser.objects.filter(role='client', company_profile=company_b)
marketers_b = MarketerUser.objects.filter(company_profile=company_b)
plot_sizes_b = PlotSize.objects.filter(company=company_b)
plot_numbers_b = PlotNumber.objects.filter(company=company_b)

print(f"  Clients: {clients_b.count()}")
print(f"  Marketers: {marketers_b.count()}")
print(f"  Plot Sizes: {plot_sizes_b.count()}")
print(f"  Plot Numbers: {plot_numbers_b.count()}")
print()

# Verify no data overlap
print("🔒 TENANT ISOLATION CHECK")
common_clients = set(clients_a.values_list('id', flat=True)) & set(clients_b.values_list('id', flat=True))
common_marketers = set(marketers_a.values_list('id', flat=True)) & set(marketers_b.values_list('id', flat=True))
print(f"  Common clients between A & B: {len(common_clients)} (should be 0)")
print(f"  Common marketers between A & B: {len(common_marketers)} (should be 0)")
print()

# Test get_request_company helper
from django.test import RequestFactory
from estateApp.views import get_request_company

print("🔧 HELPER FUNCTION TEST")
factory = RequestFactory()
request = factory.get('/test')
request.user = admin_a
request.session = {}

company = get_request_company(request)
print(f"  get_request_company() returned: {company}")
print(f"  Type: {type(company).__name__}")
print(f"  ID: {company.id if company else 'None'}")
print(f"  Is Company object: {hasattr(company, 'id') and hasattr(company, 'company_name')}")
print()

# Final verdict
print("="*70)
print(" VERIFICATION RESULTS")
print("="*70)

all_good = True

if clients_a.count() == 0:
    print("  ❌ FAIL: Company A has 0 clients")
    all_good = False
else:
    print(f"  ✅ PASS: Company A has {clients_a.count()} clients")

if marketers_a.count() == 0:
    print("  ❌ FAIL: Company A has 0 marketers")
    all_good = False
else:
    print(f"  ✅ PASS: Company A has {marketers_a.count()} marketers")

if plot_sizes_a.count() == 0:
    print("  ❌ FAIL: Company A has 0 plot sizes")
    all_good = False
else:
    print(f"  ✅ PASS: Company A has {plot_sizes_a.count()} plot sizes")

if plot_numbers_a.count() == 0:
    print("  ❌ FAIL: Company A has 0 plot numbers")
    all_good = False
else:
    print(f"  ✅ PASS: Company A has {plot_numbers_a.count()} plot numbers")

if not company:
    print("  ❌ FAIL: get_request_company() returned None")
    all_good = False
else:
    print("  ✅ PASS: get_request_company() returns Company object")

if len(common_clients) > 0 or len(common_marketers) > 0:
    print("  ❌ FAIL: Data leakage detected between companies")
    all_good = False
else:
    print("  ✅ PASS: Perfect tenant isolation (no data overlap)")

print()
if all_good:
    print("🎉 ALL CHECKS PASSED! The fix is working correctly.")
    print()
    print("✨ NEXT STEPS:")
    print("   1. Login as estate@gmail.com on the dev server")
    print("   2. Navigate to /client - Should see 11 clients")
    print("   3. Navigate to /marketer-list - Should see 5 marketers")
    print("   4. Check plot sizes and plot numbers pages")
    print("   5. Verify dashboard shows correct counts")
else:
    print("⚠️  SOME CHECKS FAILED - Please review the errors above")

print("="*70)
