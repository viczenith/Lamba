"""
Fix BillingHistory table structure to match the model definition.
"""
import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'estateProject.settings'

import django
django.setup()

from django.db import connection

cursor = connection.cursor()

# Check current structure
print("Current BillingHistory structure:")
cursor.execute("PRAGMA table_info(estateApp_billinghistory)")
for col in cursor.fetchall():
    print(f"  {col[1]}: {col[2]}")

# Since this is empty, we can safely recreate it
print("\nRecreating BillingHistory table with correct structure...")

# Drop the old table
cursor.execute("DROP TABLE IF EXISTS estateApp_billinghistory")

# Create new table with correct structure
cursor.execute("""
CREATE TABLE estateApp_billinghistory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    billing_id bigint NOT NULL REFERENCES estateApp_subscriptionbillingmodel(id),
    transaction_type varchar(20) NOT NULL,
    state varchar(20) NOT NULL DEFAULT 'pending',
    amount decimal(12, 2) NOT NULL,
    currency varchar(3) NOT NULL DEFAULT 'NGN',
    description text NOT NULL,
    transaction_id varchar(255) NOT NULL UNIQUE,
    billing_date datetime NOT NULL,
    due_date date NOT NULL,
    paid_date datetime NULL,
    invoice_number varchar(100) NOT NULL UNIQUE,
    payment_method varchar(20) NULL,
    created_at datetime NOT NULL,
    updated_at datetime NOT NULL
)
""")

print("BillingHistory table recreated successfully!")

# Verify new structure
print("\nNew BillingHistory structure:")
cursor.execute("PRAGMA table_info(estateApp_billinghistory)")
for col in cursor.fetchall():
    print(f"  {col[1]}: {col[2]}")

print("\nDone! Now run: python manage.py create_demo_transactions")
