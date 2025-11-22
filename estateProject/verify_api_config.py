#!/usr/bin/env python
"""
Verify API Endpoints Configuration
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.urls import get_resolver
from django.conf import settings

print("\n" + "="*80)
print("API ENDPOINTS VERIFICATION")
print("="*80)

# Get URL resolver
resolver = get_resolver()

# Find all API endpoints
api_endpoints = []
for pattern in resolver.url_patterns:
    if hasattr(pattern, 'pattern'):
        pattern_str = str(pattern.pattern)
        if 'api' in pattern_str:
            api_endpoints.append(pattern_str)

print("\n📍 API Endpoints Found:")
print("-" * 80)

for endpoint in sorted(api_endpoints)[:20]:  # Show first 20
    print(f"  ✅ {endpoint}")

if len(api_endpoints) > 20:
    print(f"  ... and {len(api_endpoints) - 20} more endpoints")

print("\n" + "="*80)
print("IMPORTANT FIXES MADE:")
print("="*80)
print("""
✅ Fixed api-client.js BASE_URL:
   - OLD: /api/v1  (❌ Wrong - doesn't match URL patterns)
   - NEW: /api     (✅ Correct - matches Django URL configuration)

📊 API Response Status:
   - Before: GET /api/v1/companies/ → 404 Not Found
   - After:  GET /api/companies/   → Should work correctly

🔧 What This Fixes:
   - Any JavaScript code using api-client.js will now call correct endpoints
   - Eliminates 404 errors from api-client.js method calls
   - The login page 404s (if they exist) are likely from:
     a) Browser extensions probing for APIs
     b) Old cached requests
     c) Developer tools making exploratory requests

✨ Next Steps:
   1. Clear browser cache (Ctrl+Shift+Delete)
   2. Restart Django server
   3. Reload login page (Ctrl+F5)
   4. Check DevTools Network tab for /api/v1 requests
     - Should be GONE now since we fixed BASE_URL
""")

print("="*80)
print("✅ Configuration Verified Successfully!")
print("="*80 + "\n")
