#!/usr/bin/env python3
"""
Fix marketer leakage vulnerabilities in estateApp/views.py
Both admin_marketer_profile and marketer_profile functions
"""

import re

file_path = 'estateApp/views.py'

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern 1: Fix in admin_marketer_profile (line ~1746) 
# Look for the function marker and the loop
pattern1 = r'(def admin_marketer_profile\(request, pk\):.*?# — Build leaderboard —\s+sales_data = \[\])\s+for m in MarketerUser\.objects\.all\(\):'

replacement1 = r'''\1
    # SECURITY: Filter by company to prevent cross-tenant leakage
    company = getattr(request, 'company', None) or request.user.company_profile
    company_marketers = MarketerUser.objects.filter(company=company) if company else MarketerUser.objects.none()
    
    for m in company_marketers:'''

content = re.sub(pattern1, replacement1, content, count=1, flags=re.DOTALL)

# Pattern 2: Fix in marketer_profile (line ~3636)
# Look for the function marker and the loop
pattern2 = r'(def marketer_profile\(request\):.*?# — Build leaderboard —\s+sales_data = \[\])\s+for m in MarketerUser\.objects\.all\(\):'

replacement2 = r'''\1
    # SECURITY: Filter by company to prevent cross-tenant leakage  
    company = request.user.company_profile
    company_marketers = MarketerUser.objects.filter(company=company) if company else MarketerUser.objects.none()
    
    for m in company_marketers:'''

content = re.sub(pattern2, replacement2, content, count=1, flags=re.DOTALL)

# Pattern 3: Fix Transaction query in admin_marketer_profile to include company filter
pattern3a = r'(def admin_marketer_profile\(request, pk\):.*?for m in company_marketers:\s+year_sales = Transaction\.objects\.filter\(\s+marketer=m,)((\s+transaction_date__year=current_year)(\s+\)\.aggregate))'

replacement3a = r'\1\n            company=company,\2'

content = re.sub(pattern3a, replacement3a, content, count=1, flags=re.DOTALL)

# Pattern 4: Fix MarketerTarget query in admin_marketer_profile to include company filter
pattern4a = r'(def admin_marketer_profile\(request, pk\):.*?tgt = \(\s+MarketerTarget\.objects\.filter\(marketer=m),(\s+period_type)'

replacement4a = r'\1, company=company\2'

content = re.sub(pattern4a, replacement4a, content, count=1, flags=re.DOTALL)

# Also fix the fallback MarketerTarget filter
pattern4b = r'(def admin_marketer_profile\(request, pk\):.*?or\s+MarketerTarget\.objects\.filter\(marketer=None),(\s+period_type)'

replacement4b = r'\1, company=company\2'

content = re.sub(pattern4b, replacement4b, content, count=1, flags=re.DOTALL)

# Now do same for marketer_profile function
# Pattern 5: Fix Transaction query in marketer_profile
pattern5a = r'(def marketer_profile\(request\):.*?for m in company_marketers:\s+year_sales = Transaction\.objects\.filter\(\s+marketer=m,)((\s+transaction_date__year=current_year)(\s+\)\.aggregate))'

replacement5a = r'\1\n            company=company,\2'

content = re.sub(pattern5a, replacement5a, content, count=1, flags=re.DOTALL)

# Pattern 6: Fix MarketerTarget queries in marketer_profile
pattern6a = r'(def marketer_profile\(request\):.*?for m in company_marketers:.*?tgt = \(\s+MarketerTarget\.objects\.filter\(marketer=m),(\s+period_type)'

replacement6a = r'\1, company=company\2'

content = re.sub(pattern6a, replacement6a, content, count=1, flags=re.DOTALL)

pattern6b = r'(def marketer_profile\(request\):.*?or\s+MarketerTarget\.objects\.filter\(marketer=None),(\s+period_type)'

replacement6b = r'\1, company=company\2'

content = re.sub(pattern6b, replacement6b, content, count=1, flags=re.DOTALL)

# Write the file back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed marketer leakage vulnerabilities in both functions")
print("✅ admin_marketer_profile: Added company filtering to marketer loop and queries")
print("✅ marketer_profile: Added company filtering to marketer loop and queries")
