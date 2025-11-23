#!/usr/bin/env python3
"""Fix syntax errors from the regex replacements"""

file_path = 'estateApp/views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line ~1758: Missing comma after company=company
for i, line in enumerate(lines):
    # Fix in admin_marketer_profile function area (around line 1758)
    if 'MarketerTarget.objects.filter(marketer=m, company=company period_type=' in line:
        lines[i] = line.replace('company=company period_type=', 'company=company, period_type=')
        print(f"✅ Fixed syntax error on line {i+1}: Added missing comma")

# Also fix the second function's queries if they have the same issue
for i, line in enumerate(lines):
    if 'MarketerTarget.objects.filter(marketer=None, company=company period_type=' in line:
        lines[i] = line.replace('company=company period_type=', 'company=company, period_type=')
        print(f"✅ Fixed syntax error on line {i+1}: Added missing comma (fallback filter)")

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ All syntax errors fixed")
