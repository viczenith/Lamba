import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'estateProject.settings'

import django
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]

billing_tables = [t for t in tables if 'billing' in t.lower()]
print("Billing tables:", billing_tables)

# Check BillingHistory columns
for table in billing_tables:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    print(f"\nColumns in {table}:")
    for col in columns:
        print(f"  {col[1]}: {col[2]}")
