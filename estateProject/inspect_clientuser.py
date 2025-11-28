#!/usr/bin/env python
import os, django, sys
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser
print("ClientUser columns:")
for f in ClientUser._meta.local_fields:
    print(f"  {f.name} -> column: {getattr(f,'column',None)}")
print(f"\ndb_table: {ClientUser._meta.db_table}")
