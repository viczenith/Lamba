import os
import django
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import PlotSize, PlotNumber

print("=" * 80)
print("🔍 PLOTSIZE & PLOTNUMBER RECORDS ANALYSIS")
print("=" * 80)

# Check all plot sizes
all_sizes = PlotSize.objects.all()
print(f"\nTotal PlotSize records: {all_sizes.count()}")
print("\nDetails:")
for ps in all_sizes:
    company_name = ps.company.company_name if ps.company else "❌ NO COMPANY (NULL)"
    print(f"  ID {ps.id:2d}: {ps.size:10s} | Company: {company_name}")

# Check all plot numbers
all_numbers = PlotNumber.objects.all()
print(f"\n\nTotal PlotNumber records: {all_numbers.count()}")
print("\nDetails:")
for pn in all_numbers:
    company_name = pn.company.company_name if pn.company else "❌ NO COMPANY (NULL)"
    print(f"  ID {pn.id:2d}: {pn.number:10s} | Company: {company_name}")

# Check for NULL company_id in database
print("\n" + "=" * 80)
print("🔍 DATABASE ANALYSIS")
print("=" * 80)

db_path = r'c:\Users\HP\Documents\VictorGodwin\RE\Multi-Tenant Architecture\RealEstateMSApp\estateProject\db.sqlite3'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM estateApp_plotsize WHERE company_id IS NULL")
null_sizes = cursor.fetchone()[0]
print(f"\nPlotSize records with NULL company_id: {null_sizes}")

cursor.execute("SELECT COUNT(*) FROM estateApp_plotnumber WHERE company_id IS NULL")
null_numbers = cursor.fetchone()[0]
print(f"PlotNumber records with NULL company_id: {null_numbers}")

if null_sizes > 0:
    print("\n⚠️  CRITICAL: Old PlotSize records exist without company assignment!")
    print("    These will be visible to ALL companies!")
    
if null_numbers > 0:
    print("\n⚠️  CRITICAL: Old PlotNumber records exist without company assignment!")
    print("    These will be visible to ALL companies!")

conn.close()

print("\n" + "=" * 80)
print("SOLUTION: Assign company to all NULL records or delete them")
print("=" * 80)
