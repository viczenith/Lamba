#!/usr/bin/env python
"""Check all data currently in the Lamba System database"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import CustomUser, Company, Estate, EstatePlot, PlotAllocation
from django.db import connection

print("\n" + "="*70)
print("🗄️  LAMBA SYSTEM - DATABASE CONTENTS")
print("="*70)

# Check Users
print("\n📊 USERS TABLE")
print("-" * 70)
users = CustomUser.objects.all()
print(f"Total Users: {users.count()}")
if users.exists():
    print("\nUser Details:")
    for i, user in enumerate(users[:20], 1):
        print(f"\n{i}. Email: {user.email}")
        print(f"   Full Name: {user.full_name}")
        print(f"   Phone: {user.phone}")
        print(f"   Role: {user.role}")
        print(f"   Is Staff: {user.is_staff}")
        print(f"   Is Superuser: {user.is_superuser}")
        print(f"   Active: {user.is_active}")
        if user.company_profile:
            print(f"   Company: {user.company_profile.company_name}")
else:
    print("❌ No users found in database")

# Check Companies
print("\n\n📊 COMPANIES TABLE")
print("-" * 70)
companies = Company.objects.all()
print(f"Total Companies: {companies.count()}")
if companies.exists():
    print("\nCompany Details:")
    for i, company in enumerate(companies[:20], 1):
        print(f"\n{i}. Company Name: {company.company_name}")
        print(f"   Subdomain: {company.subdomain}")
        print(f"   Status: {company.status}")
        print(f"   Created: {company.created_at}")
        # Count users in this company
        company_users = CustomUser.objects.filter(company_profile=company).count()
        print(f"   Total Users: {company_users}")
else:
    print("❌ No companies found in database")

# Check Estates
print("\n\n📊 ESTATES TABLE")
print("-" * 70)
estates = Estate.objects.all()
print(f"Total Estates: {estates.count()}")
if estates.exists():
    print("\nRecent Estates:")
    for i, estate in enumerate(estates[:10], 1):
        print(f"\n{i}. Name: {estate.name}")
        print(f"   Location: {estate.location}")
        print(f"   Status: {estate.status}")
        if estate.company_profile:
            print(f"   Company: {estate.company_profile.company_name}")
else:
    print("❌ No estates found in database")

# Check Estate Plots
print("\n\n📊 ESTATE PLOTS TABLE")
print("-" * 70)
plots = EstatePlot.objects.all()
print(f"Total Plots: {plots.count()}")
if plots.exists():
    print("\nRecent Plots:")
    for i, plot in enumerate(plots[:10], 1):
        print(f"\n{i}. Plot Number: {plot.plot_number}")
        print(f"   Estate: {plot.estate.name}")
        print(f"   Status: {plot.status}")
        print(f"   Price: {plot.price}")
else:
    print("❌ No plots found in database")

# Check Plot Allocations
print("\n\n📊 PLOT ALLOCATIONS TABLE")
print("-" * 70)
allocations = PlotAllocation.objects.all()
print(f"Total Allocations: {allocations.count()}")
if allocations.exists():
    print("\nRecent Allocations:")
    for i, alloc in enumerate(allocations[:10], 1):
        print(f"\n{i}. Client: {alloc.client.full_name}")
        print(f"   Plot: {alloc.plot.plot_number}")
        print(f"   Status: {alloc.status}")
        print(f"   Allocated: {alloc.allocation_date}")
else:
    print("❌ No plot allocations found in database")

# Check all tables in database
print("\n\n📊 ALL DATABASE TABLES")
print("-" * 70)
with connection.cursor() as cursor:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = cursor.fetchall()
    print(f"Total Tables: {len(tables)}")
    print("\nTables:")
    for i, table in enumerate(tables, 1):
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        print(f"{i:3}. {table_name:50} ({count} records)")

print("\n" + "="*70)
print("✅ Database check complete!")
print("="*70 + "\n")
