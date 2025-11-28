#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from estateApp.models import ClientUser, CustomUser

test_user_id = 14

print("Test User ID:", test_user_id)

# Check if it exists as CustomUser
custom_exists = CustomUser.objects.filter(id=test_user_id).exists()
print(f"CustomUser exists: {custom_exists}")

# Check if it exists as ClientUser
client_exists = ClientUser.objects.filter(pk=test_user_id).exists()
print(f"ClientUser.objects.filter(pk=...) exists: {client_exists}")

client_exists2 = ClientUser.objects.filter(customuser_ptr_id=test_user_id).exists()
print(f"ClientUser.objects.filter(customuser_ptr_id=...) exists: {client_exists2}")

client_exists3 = ClientUser.objects.filter(id=test_user_id).exists()
print(f"ClientUser.objects.filter(id=...) exists: {client_exists3}")

# Try to get it
try:
    obj = ClientUser.objects.get(pk=test_user_id)
    print(f"\n✅ Got ClientUser: {obj.email}")
except ClientUser.DoesNotExist:
    print(f"\n❌ ClientUser does not exist")

# Check the raw data
from django.db import connection
cursor = connection.cursor()

cursor.execute("SELECT * FROM estateapp_clientuser WHERE customuser_ptr_id = ?", [test_user_id])
rows = cursor.fetchall()
print(f"\nRaw SQL query results: {len(rows)} rows")
if rows:
    for row in rows:
        print(f"  {row}")
