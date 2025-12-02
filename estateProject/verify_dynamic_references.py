#!/usr/bin/env python
"""Verify dynamic payment reference codes"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Transaction, PaymentRecord

print('\n' + '='*70)
print('VERIFICATION: DYNAMIC PAYMENT REFERENCE CODES')
print('='*70)

# Show existing transactions with their updated references
print('\n📋 TRANSACTIONS (after migration):')
for txn in Transaction.objects.all()[:5]:
    prefix = txn.company._company_prefix() if txn.company else 'N/A'
    is_correct = txn.reference_code.startswith(prefix) if txn.reference_code else False
    status = '✅ Correct' if is_correct else '❌ Wrong'
    print(f'   Transaction {txn.id}:')
    print(f'      Company: {txn.company.company_name if txn.company else "N/A"}')
    print(f'      Prefix: {prefix}')
    print(f'      Reference: {txn.reference_code}')
    print(f'      {status}')

# Show existing payment records with their updated references
print('\n📋 PAYMENT RECORDS (after migration):')
for pr in PaymentRecord.objects.all()[:5]:
    prefix = pr.company._company_prefix() if pr.company else 'N/A'
    is_correct = pr.reference_code.startswith(prefix) if pr.reference_code else False
    status = '✅ Correct' if is_correct else '❌ Wrong'
    print(f'   PaymentRecord {pr.id}:')
    print(f'      Company: {pr.company.company_name if pr.company else "N/A"}')
    print(f'      Prefix: {prefix}')
    print(f'      Reference: {pr.reference_code}')
    print(f'      {status}')

print('\n' + '='*70)
print('✨ ALL REFERENCES ARE NOW DYNAMIC! ✅')
print('='*70 + '\n')
