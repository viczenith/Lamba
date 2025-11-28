#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from estateApp.models import ClientUser, MarketerUser, CustomUser

print("ClientUser model fields:")
for field in ClientUser._meta.get_fields():
    print(f"  {field.name}: {field.__class__.__name__}")

print("\n\nMarketerUser model fields:")
for field in MarketerUser._meta.get_fields():
    print(f"  {field.name}: {field.__class__.__name__}")

print("\n\nCustomUser model fields:")
for field in CustomUser._meta.get_fields():
    print(f"  {field.name}: {field.__class__.__name__}")
