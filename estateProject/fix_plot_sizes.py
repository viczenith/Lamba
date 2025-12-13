"""
Script to fix PlotSize values - standardize to "X sqm" format
"""
import os
import re
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.db import connection

print('=' * 50)
print('INSPECTING CURRENT PLOT SIZE VALUES')
print('=' * 50)

with connection.cursor() as cursor:
    cursor.execute('SELECT id, size, company_id FROM estateApp_plotsize')
    rows = cursor.fetchall()
    
    print(f"{'ID':<5} | {'Current Size':<20} | {'Company':<10}")
    print('-' * 50)
    for row in rows:
        print(f"{row[0]:<5} | {row[1]:<20} | {row[2]:<10}")

print('\n' + '=' * 50)
print('FIXING PLOT SIZE VALUES')
print('=' * 50)

with connection.cursor() as cursor:
    cursor.execute('SELECT id, size FROM estateApp_plotsize')
    rows = cursor.fetchall()
    
    fixed = 0
    for row in rows:
        plot_id = row[0]
        original = str(row[1])
        
        # Extract numeric value (including decimals)
        numeric_match = re.search(r'[\d.]+', original)
        
        if numeric_match:
            numeric_value = numeric_match.group()
            # Remove trailing zeros and decimal point if whole number
            if '.' in numeric_value:
                numeric_value = numeric_value.rstrip('0').rstrip('.')
            
            new_value = f'{numeric_value} sqm'
            
            if original != new_value:
                print(f'ID {plot_id}: "{original}" -> "{new_value}"')
                cursor.execute(
                    'UPDATE estateApp_plotsize SET size = %s WHERE id = %s',
                    [new_value, plot_id]
                )
                fixed += 1
            else:
                print(f'ID {plot_id}: "{original}" - Already correct')
        else:
            print(f'ID {plot_id}: "{original}" - Could not extract number, skipping')

print(f'\n✅ Fixed {fixed} records')

# Verify
print('\n' + '=' * 50)
print('VERIFICATION - UPDATED VALUES')
print('=' * 50)

with connection.cursor() as cursor:
    cursor.execute('SELECT id, size, company_id FROM estateApp_plotsize')
    rows = cursor.fetchall()
    
    print(f"{'ID':<5} | {'New Size':<20} | {'Company':<10}")
    print('-' * 50)
    for row in rows:
        print(f"{row[0]:<5} | {row[1]:<20} | {row[2]:<10}")

print('\n✅ Database fix complete!')
