import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company, PlotSize, PlotNumber, Estate, EstatePlot, PlotSizeUnits
from django.db.models import Prefetch

print("=" * 80)
print("🔍 COMPREHENSIVE DATA LEAKAGE AUDIT")
print("=" * 80)

# Get companies
companies = list(Company.objects.all()[:2])
if len(companies) < 2:
    print("Not enough companies to test")
    exit(1)

company_a, company_b = companies

print(f"\n🏢 Company A: {company_a.company_name}")
print(f"🏢 Company B: {company_b.company_name}")

# Clean up old test data
PlotSize.objects.filter(company__in=companies).delete()
PlotNumber.objects.filter(company__in=companies).delete()

# Create test data
print("\n" + "=" * 80)
print("Creating test data...")
print("=" * 80)

ps_a1 = PlotSize.objects.create(company=company_a, size="500sqm")
ps_a2 = PlotSize.objects.create(company=company_a, size="1000sqm")
print(f"✓ Company A PlotSizes: 500sqm, 1000sqm")

ps_b1 = PlotSize.objects.create(company=company_b, size="500sqm")
ps_b2 = PlotSize.objects.create(company=company_b, size="2000sqm")
print(f"✓ Company B PlotSizes: 500sqm, 2000sqm")

pn_a1 = PlotNumber.objects.create(company=company_a, number="A-001")
pn_a2 = PlotNumber.objects.create(company=company_a, number="A-002")
print(f"✓ Company A PlotNumbers: A-001, A-002")

pn_b1 = PlotNumber.objects.create(company=company_b, number="A-001")
pn_b2 = PlotNumber.objects.create(company=company_b, number="B-001")
print(f"✓ Company B PlotNumbers: A-001, B-001")

# Now test all problematic query patterns
print("\n" + "=" * 80)
print("Testing various query patterns for leakage...")
print("=" * 80)

errors = []

# Test 1: Direct all() queries
print("\n1️⃣  Direct .all() queries")
all_sizes = PlotSize.objects.all()
all_numbers = PlotNumber.objects.all()
print(f"   PlotSize.objects.all(): {all_sizes.count()} records")
print(f"   - Company A should see 2, Company B should see 2")
print(f"   ⚠️  WARNING: This query returns ALL regardless of company!")
errors.append("PlotSize.objects.all() lacks company filtering")
errors.append("PlotNumber.objects.all() lacks company filtering")

# Test 2: Prefetch queries (used in view_allocated_plot)
print("\n2️⃣  Prefetch_related queries")
estate = Estate.objects.first()
if estate:
    prefetched = Estate.objects.prefetch_related(
        Prefetch('estate_plots',
            queryset=EstatePlot.objects.prefetch_related(
                Prefetch('plot_numbers', 
                    queryset=PlotNumber.objects.prefetch_related('plotallocation_set')
                )
            )
        )
    ).first()
    if prefetched and prefetched.estate_plots.exists():
        for ep in prefetched.estate_plots.all():
            plot_numbers = ep.plot_numbers.all()
            print(f"   Estate {ep.estate.name if ep.estate else 'N/A'}: {plot_numbers.count()} plot numbers")
            if plot_numbers.count() > 0:
                print(f"   ⚠️  Plot numbers visible: {[p.number for p in plot_numbers]}")
                errors.append("Prefetch plot_numbers not company-scoped")

# Test 3: Filter with joins (used in add_floor_plan)
print("\n3️⃣  Filter queries with joins")
sizes_for_estate = PlotSize.objects.filter(
    plotsizeunits__estate_plot__estate__isnull=False
).distinct()
print(f"   PlotSize with joins: {sizes_for_estate.count()} records")
if sizes_for_estate.count() > 0:
    for ps in sizes_for_estate:
        if ps.company:
            print(f"   - {ps.size} (Company: {ps.company.company_name})")
        else:
            print(f"   - {ps.size} (NO COMPANY!) ⚠️")
            errors.append(f"PlotSize {ps.size} has no company assigned!")

# Test 4: Check PlotSizeUnits associations
print("\n4️⃣  PlotSizeUnits associations")
for company in companies:
    psu_count = PlotSizeUnits.objects.filter(
        plot_size__company=company
    ).count()
    print(f"   {company.company_name}: {psu_count} PlotSizeUnits")

# Test 5: Cross-company visibility simulation
print("\n5️⃣  Cross-company visibility test")
print(f"\n   If Company B admin views Company A's estate:")

# Simulate what Company B would see if visiting Company A's data
try:
    # This should fail or return empty if proper isolation
    estate_a = Estate.objects.first()
    if estate_a:
        # Try to get plot sizes for this estate WITHOUT company filtering
        unfiltered_sizes = PlotSize.objects.filter(
            plotsizeunits__estate_plot__estate=estate_a
        ).distinct()
        
        print(f"   - Unfiltered query returns: {unfiltered_sizes.count()} plot sizes")
        if unfiltered_sizes.count() > 0:
            for ps in unfiltered_sizes:
                company_name = ps.company.company_name if ps.company else "UNKNOWN"
                print(f"     └─ {ps.size} (Owner: {company_name})")
                if ps.company and ps.company != company_a:
                    errors.append(f"Cross-company visibility: {company_name}'s data visible without filter")
except Exception as e:
    print(f"   Error: {e}")

# Results
print("\n" + "=" * 80)
if errors:
    print("❌ ISSUES FOUND:")
    for i, error in enumerate(errors, 1):
        print(f"   {i}. {error}")
    print("\n⚠️  DATA ISOLATION INCOMPLETE - LEAKAGE STILL POSSIBLE")
else:
    print("✅ NO DIRECT ISSUES FOUND")
    print("\n📝 NOTE: The following patterns can still cause leakage:")
    print("   1. Templates rendering PlotSize.objects.all() without filtering")
    print("   2. JavaScript/AJAX endpoints returning unfiltered data")
    print("   3. Forms with choices populated from PlotSize.objects.all()")
    print("   4. Exports/Reports using global queries")
print("=" * 80)

# Cleanup
PlotSize.objects.filter(company__in=companies).delete()
PlotNumber.objects.filter(company__in=companies).delete()
print("\n✓ Test data cleaned up")
