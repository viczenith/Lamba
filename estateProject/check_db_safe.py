#!/usr/bin/env python
"""Check all data currently in the Lamba System database - Safe version"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import CustomUser, Company
from django.db import connection

print("\n" + "="*70)
print("🗄️  LAMBA SYSTEM - DATABASE CONTENTS")
print("="*70)

# Check Users using only() to avoid is_system_admin field
print("\n📊 USERS TABLE")
print("-" * 70)
users = CustomUser.objects.only('email', 'full_name', 'phone', 'role', 'is_staff', 'is_superuser', 'is_active').all()
print(f"Total Users: {users.count()}")

if users.count() > 0:
    print("\n🔐 ADMIN USERS:")
    admins = [u for u in users if u.role == 'admin']
    if admins:
        for i, user in enumerate(admins, 1):
            print(f"\n{i}. Email: {user.email}")
            print(f"   Full Name: {user.full_name}")
            print(f"   Phone: {user.phone}")
            print(f"   Role: {user.role}")
            print(f"   Is Staff: {'✅' if user.is_staff else '❌'}")
            print(f"   Is Superuser: {'✅' if user.is_superuser else '❌'}")
            print(f"   Active: {'✅' if user.is_active else '❌'}")
    else:
        print("   ❌ No admin users found")
    
    print("\n\n👥 ALL USERS BY ROLE:")
    roles = {}
    for user in users:
        role = user.role or 'No Role'
        if role not in roles:
            roles[role] = []
        roles[role].append(user)
    
    for role, role_users in roles.items():
        print(f"\n   {role.upper()}: {len(role_users)} users")
        for user in role_users[:5]:  # Show first 5
            print(f"      - {user.email} | {user.full_name}")
        if len(role_users) > 5:
            print(f"      ... and {len(role_users) - 5} more")
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
        try:
            company_users = CustomUser.objects.filter(company_profile=company).count()
            print(f"   Total Users: {company_users}")
        except:
            print(f"   Total Users: Unable to count")
else:
    print("❌ No companies found in database")

# Check all tables in database
print("\n\n📊 ALL DATABASE TABLES")
print("-" * 70)
with connection.cursor() as cursor:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = cursor.fetchall()
    print(f"Total Tables: {len(tables)}")
    print("\nTables with Record Counts:")
    
    estate_tables = []
    auth_tables = []
    admin_tables = []
    other_tables = []
    
    for table in tables:
        table_name = table[0]
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            
            table_info = f"{table_name:50} ({count:>5} records)"
            
            if 'estate' in table_name.lower():
                estate_tables.append(table_info)
            elif 'auth' in table_name.lower() or 'user' in table_name.lower() or 'permission' in table_name.lower():
                auth_tables.append(table_info)
            elif 'admin' in table_name.lower() or 'super' in table_name.lower():
                admin_tables.append(table_info)
            else:
                other_tables.append(table_info)
        except:
            pass
    
    if estate_tables:
        print("\n   📍 ESTATE RELATED:")
        for i, t in enumerate(estate_tables, 1):
            print(f"   {i:3}. {t}")
    
    if auth_tables:
        print("\n   🔐 AUTHENTICATION & USERS:")
        for i, t in enumerate(auth_tables, 1):
            print(f"   {i:3}. {t}")
    
    if admin_tables:
        print("\n   ⚙️ ADMIN TABLES:")
        for i, t in enumerate(admin_tables, 1):
            print(f"   {i:3}. {t}")
    
    if other_tables:
        print("\n   📦 OTHER TABLES:")
        for i, t in enumerate(other_tables, 1):
            print(f"   {i:3}. {t}")

print("\n" + "="*70)
print("✅ Database check complete!")
print("\n⚠️  NOTE: New admin fields (is_system_admin, admin_level) need migration")
print("    Run: python manage.py makemigrations && python manage.py migrate")
print("="*70 + "\n")
