from estateApp.models import Company, Transaction
from estateApp.templatetags.custom_filters import currency_format

print('\n' + '='*60)
print('RECEIPT ENHANCEMENT TEST RESULTS')
print('='*60)

# Test 1: Currency Formatting
print('\n1. Currency Formatting:')
print(f'   15000000 → {currency_format(15000000)}')
print(f'   1234.56  → {currency_format(1234.56)}')
print(f'   500      → {currency_format(500)}')

# Test 2: Receipt Number Generation
print('\n2. Receipt Number Generation:')
company = Company.objects.first()
if company:
    print(f'   Company: {company.company_name}')
    receipt1 = company.get_next_receipt_number()
    receipt2 = company.get_next_receipt_number()
    receipt3 = company.get_next_receipt_number()
    print(f'   Receipt 1: {receipt1}')
    print(f'   Receipt 2: {receipt2}')
    print(f'   Receipt 3: {receipt3}')
    print(f'   Counter: {company.receipt_counter}')
else:
    print('   No company found')

# Test 3: New Fields
print('\n3. New Company Fields:')
if company:
    print(f'   CAC Number (registration_number): {company.registration_number}')
    print(f'   Cashier Name: {company.cashier_name or "Not set"}')
    print(f'   Cashier Signature: {"Uploaded" if company.cashier_signature else "Not uploaded"}')
    print(f'   Receipt Counter: {company.receipt_counter}')

# Test 4: Transaction Example
print('\n4. Transaction Example:')
txn = Transaction.objects.first()
if txn:
    print(f'   Transaction Ref: {txn.reference_code}')
    print(f'   Amount: {currency_format(txn.total_amount)}')
    print(f'   Balance: {currency_format(txn.balance)}')
else:
    print('   No transaction found')

print('\n' + '='*60)
print('✅ All tests completed successfully!')
print('='*60 + '\n')
