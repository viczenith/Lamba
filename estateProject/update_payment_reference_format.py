#!/usr/bin/env python
"""
Update PaymentRecord reference codes to use consistent format (no dash after prefix).

Before: LPL-20251128-500-9654
After:  LPL20251128-500-9654

This ensures both Transaction and PaymentRecord use identical format.
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

import re
from estateApp.models import PaymentRecord

print('\n' + '='*70)
print('UPDATING PAYMENTRECORD REFERENCE CODES - UNIFIED FORMAT')
print('='*70)

payments = PaymentRecord.objects.all()
updated = 0

print(f'\n📋 Found {payments.count()} payment records to process...')

for pr in payments:
    if not pr.reference_code:
        continue
    
    # Pattern: LPL-20251128-500-9654 or LPL-20251128-500BAN9654
    # Remove the dash after the prefix
    old_code = pr.reference_code
    
    # Match: {PREFIX}-{REST}
    match = re.match(r'^([A-Z0-9]{2,3})-(.+)$', pr.reference_code)
    
    if match:
        prefix = match.group(1)
        rest = match.group(2)
        new_code = f"{prefix}{rest}"  # Remove the dash
        
        if old_code != new_code:
            pr.reference_code = new_code
            pr.save(update_fields=['reference_code'])
            updated += 1
            print(f'   ✅ {old_code} → {new_code}')

print(f'\n📊 Results: {updated} payment records updated')
print('='*70)
print('✨ All payment records now use unified format (no dash after prefix)')
print('='*70 + '\n')
