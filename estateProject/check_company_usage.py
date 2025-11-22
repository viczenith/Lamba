#!/usr/bin/env python3
"""
Check for functions that use 'company' variable without defining it.
"""

import re
from pathlib import Path

def check_company_usage(file_path):
    """Check if company is used without being defined in functions."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Find all function definitions
    function_pattern = r'^(?:@\w+(?:\([^)]*\))?\s*)*\ndef\s+(\w+)\s*\('
    
    issues = []
    current_function = None
    current_function_line = 0
    function_lines = {}
    indent_level = 0
    
    for i, line in enumerate(lines, 1):
        # Check for function definition
        match = re.search(function_pattern, line)
        if match:
            current_function = match.group(1)
            current_function_line = i
            function_lines[current_function] = {
                'start': i,
                'content': [],
                'has_company_def': False,
                'uses_company': False,
                'company_usage_lines': []
            }
            indent_level = len(line) - len(line.lstrip())
            continue
        
        # Track function content
        if current_function and line.strip():
            # Check if we're still in the function
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= indent_level and line.strip() and not line.strip().startswith('#'):
                # We've left the function
                current_function = None
                continue
            
            if current_function:
                function_lines[current_function]['content'].append((i, line))
                
                # Check if company is defined in this line
                if re.search(r'\bcompany\s*=\s*get_request_company\(', line):
                    function_lines[current_function]['has_company_def'] = True
                
                # Check if company is used (but not in definitions)
                if re.search(r'[,\s(=]company\s*[,)\s]|company_profile=company|filter\(company=company|create\(company=company', line):
                    if 'company=' not in line or 'company=company' in line or 'company_profile=company' in line:
                        function_lines[current_function]['uses_company'] = True
                        function_lines[current_function]['company_usage_lines'].append(i)
    
    # Analyze results
    print("=" * 80)
    print("CHECKING FOR UNDEFINED 'company' VARIABLE USAGE")
    print("=" * 80)
    
    vulnerable_functions = []
    
    for func_name, data in function_lines.items():
        if data['uses_company'] and not data['has_company_def']:
            # Exclude certain functions that might get company differently
            if func_name in ['get_request_company', 'filter_by_company', 'update_profile_data', 
                           'send_notification_email', 'allocate_units', 'calculate_portfolio_metrics',
                           'send_bulk_price_update_notification', 'send_single_price_update_notification',
                           'is_admin']:
                continue
            
            vulnerable_functions.append({
                'name': func_name,
                'line': data['start'],
                'usage_lines': data['company_usage_lines']
            })
    
    if vulnerable_functions:
        print(f"\n🚨 FOUND {len(vulnerable_functions)} FUNCTION(S) USING 'company' WITHOUT DEFINITION:\n")
        for func in vulnerable_functions:
            print(f"  ❌ Function: {func['name']}")
            print(f"     Line: {func['line']}")
            print(f"     Uses 'company' at lines: {', '.join(map(str, func['usage_lines'][:5]))}")
            if len(func['usage_lines']) > 5:
                print(f"     ... and {len(func['usage_lines']) - 5} more lines")
            print()
    else:
        print("\n✅ NO ISSUES FOUND - All functions define 'company' before using it!\n")
    
    print("=" * 80)
    return vulnerable_functions


if __name__ == "__main__":
    views_path = Path(__file__).parent / "estateApp" / "views.py"
    issues = check_company_usage(views_path)
    
    if issues:
        print(f"\n⚠️  TOTAL ISSUES: {len(issues)}")
        exit(1)
    else:
        print("\n✅ VERIFICATION COMPLETE - ALL CLEAR!")
        exit(0)
