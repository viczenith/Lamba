"""
COMPLETE DATA WIPE - Start Fresh (Fixed Foreign Key Order)
Deletes all operational data while respecting foreign key constraints
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.db import connection
import sys

print("=" * 80)
print(" COMPLETE DATA WIPE - STARTING FRESH")
print("=" * 80)
print()
print("⚠️  WARNING: This will delete ALL DATA including:")
print("   - All users (clients, marketers, staff, admins)")
print("   - All estates and properties")
print("   - All transactions and payments")
print("   - All messages and notifications")
print("   - All companies")
print("   - EVERYTHING in the database")
print()
print("✅ What will be PRESERVED:")
print("   - Database schema and structure")
print("   - Migrations history")
print()

response = input("Type 'DELETE ALL DATA' to proceed: ")

if response != 'DELETE ALL DATA':
    print("\n❌ Aborted. No data was deleted.")
    sys.exit(0)

print("\n🔥 Starting complete database wipe...")
print()

try:
    cursor = connection.cursor()
    
    # Get all table names
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        AND name NOT LIKE 'django_migrations'
    """)
    
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"📊 Found {len(tables)} tables to clear")
    print()
    
    # Disable foreign key checks temporarily
    cursor.execute("PRAGMA foreign_keys = OFF")
    
    deleted_counts = {}
    
    for table in tables:
        try:
            # Count before delete
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            if count > 0:
                # Delete all data
                cursor.execute(f"DELETE FROM {table}")
                deleted_counts[table] = count
                print(f"   ✅ {table}: {count} records deleted")
        except Exception as e:
            print(f"   ⚠️  {table}: {e}")
    
    # Re-enable foreign key checks
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Commit the transaction
    connection.commit()
    
    print()
    print("=" * 80)
    print(" DATA WIPE COMPLETE")
    print("=" * 80)
    print()
    print("📊 SUMMARY:")
    total_deleted = sum(deleted_counts.values())
    print(f"   Total records deleted: {total_deleted}")
    print(f"   Tables cleared: {len(deleted_counts)}")
    print()
    
    # Show key tables
    key_tables = ['estateApp_customuser', 'estateApp_company', 'estateApp_estate', 
                  'estateApp_transaction', 'estateApp_message']
    print("📋 Key Tables:")
    for table in key_tables:
        count = deleted_counts.get(table, 0)
        print(f"   - {table}: {count} records")
    print()
    
    print("✅ DATABASE IS NOW COMPLETELY CLEAN")
    print()
    print("🎯 NEXT STEPS:")
    print("   1. Run migrations to ensure schema is correct:")
    print("      python manage.py migrate")
    print()
    print("   2. Create your first company (Company A):")
    print("      - Go to /register or use admin panel")
    print("      - Set up proper tenant structure from the start")
    print()
    print("   3. Build data incrementally:")
    print("      - Test after each addition")
    print("      - Verify tenant isolation at each step")
    print()
    print("=" * 80)

except Exception as e:
    print(f"\n❌ ERROR during data wipe: {e}")
    import traceback
    traceback.print_exc()
    connection.rollback()
