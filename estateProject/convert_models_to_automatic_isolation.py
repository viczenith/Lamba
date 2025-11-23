#!/usr/bin/env python
"""
AUTOMATED MODEL CONVERSION SCRIPT
Converts models to use TenantAwareManager for automatic query interception
"""

import os
import sys
import re
from pathlib import Path

# Models that need conversion (high priority first)
MODELS_TO_CONVERT = [
    ('PlotSize', 'estateApp/models.py'),
    ('PlotNumber', 'estateApp/models.py'),
    ('EstateProperty', 'estateApp/models.py'),
    ('Estate', 'estateApp/models.py'),
    ('Status', 'estateApp/models.py'),
    ('FloorPlan', 'estateApp/models.py'),
    ('Prototype', 'estateApp/models.py'),
    ('AllocatedPlot', 'estateApp/models.py'),
]

def find_model_class(file_path, model_name):
    """Find model class definition in file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    pattern = rf'^class {model_name}\(.*?\):\s*$'
    matches = list(re.finditer(pattern, content, re.MULTILINE))
    
    if matches:
        return matches[0].start()
    return None


def check_has_manager(file_path, model_name):
    """Check if model already has custom manager"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the model
    pattern = rf'class {model_name}\(.*?\):.*?(?=^class |\Z)'
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    
    if not match:
        return False
    
    model_content = match.group(0)
    
    # Check for any custom manager
    if 'objects =' in model_content:
        if 'TenantAwareManager' in model_content:
            return 'already_converted'
        return 'has_other_manager'
    
    return False


def has_company_field(file_path, model_name):
    """Check if model has company field"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    pattern = rf'class {model_name}\(.*?\):.*?(?=^class |\Z)'
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    
    if not match:
        return False
    
    model_content = match.group(0)
    return 'company' in model_content.lower()


def generate_conversion_report():
    """Generate report of models that need conversion"""
    print("=" * 80)
    print("MULTI-TENANT MODEL CONVERSION REPORT")
    print("=" * 80)
    print()
    
    project_root = Path(__file__).parent
    
    for model_name, file_path in MODELS_TO_CONVERT:
        full_path = project_root / file_path
        
        if not full_path.exists():
            print(f"❌ {model_name:20} - FILE NOT FOUND: {file_path}")
            continue
        
        # Check model characteristics
        has_company = has_company_field(str(full_path), model_name)
        manager_status = check_has_manager(str(full_path), model_name)
        
        status_icon = "✅" if manager_status == 'already_converted' else "⚠️"
        
        print(f"{status_icon} {model_name:20} | Company Field: {has_company:5} | Manager: {manager_status}")
    
    print()
    print("=" * 80)
    print("CONVERSION STRATEGY")
    print("=" * 80)
    print("""
STEP 1: Add TenantAwareManager to Models
    - Add: from estateApp.isolation import TenantAwareManager
    - Add: objects = TenantAwareManager() to each model
    
STEP 2: Update Views to Remove Manual Filtering
    - Remove: company=company filters from all queries
    - Views now get automatic filtering
    
STEP 3: Test Isolation
    - Run isolation tests for each model
    - Verify cross-tenant data isolation
    
STEP 4: Deploy & Monitor
    - Deploy with audit logging enabled
    - Monitor AuditLog for any isolation violations
""")


def generate_conversion_code(model_name, file_path):
    """Generate Python code snippet for model conversion"""
    
    code = f"""
# CONVERSION CODE FOR {model_name}

# Step 1: Add import at top of models.py
from estateApp.isolation import TenantAwareManager

# Step 2: Update the model class
class {model_name}(models.Model):
    # ... existing fields ...
    company = models.ForeignKey(Company, on_delete=models.CASCADE)  # Verify this exists
    
    # Add this line:
    objects = TenantAwareManager()
    
    class Meta:
        # Ensure database uniqueness is per-company
        unique_together = [('company', 'unique_field_name')]  # Update unique_field_name
        # or if single unique field:
        # unique_together = [('company', 'name')]
        
        indexes = [
            models.Index(fields=['company']),  # Performance improvement
        ]

# Step 3: Create migration
# python manage.py makemigrations
# python manage.py migrate

# Step 4: Update views - REMOVE manual company filters
# BEFORE:
#   plots = PlotSize.objects.filter(size__iexact=size, company=company)
# 
# AFTER:
#   plots = PlotSize.objects.filter(size__iexact=size)  # Auto-filtered!
"""
    
    return code


def generate_test_code(model_name):
    """Generate isolation test code"""
    
    test_code = f"""
# Isolation Test for {model_name}

from django.test import TestCase
from estateApp.models import {model_name}, Company
from estateApp.isolation import set_current_tenant, clear_tenant_context

class Test{model_name}Isolation(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(name="Company A", slug="company-a")
        self.company_b = Company.objects.create(name="Company B", slug="company-b")
        
        # Create test data
        {model_name}.objects.create(name="Item A", company=self.company_a)
        {model_name}.objects.create(name="Item B", company=self.company_b)
    
    def test_company_a_isolation(self):
        \"\"\"Company A should only see its own data\"\"\"
        set_current_tenant(company=self.company_a)
        items = {model_name}.objects.all()
        
        self.assertEqual(items.count(), 1)
        self.assertEqual(items[0].company, self.company_a)
        clear_tenant_context()
    
    def test_company_b_isolation(self):
        \"\"\"Company B should only see its own data\"\"\"
        set_current_tenant(company=self.company_b)
        items = {model_name}.objects.all()
        
        self.assertEqual(items.count(), 1)
        self.assertEqual(items[0].company, self.company_b)
        clear_tenant_context()
    
    def test_no_cross_tenant_visibility(self):
        \"\"\"Company A cannot see Company B's data\"\"\"
        set_current_tenant(company=self.company_a)
        items = {model_name}.objects.all()
        
        # Should NOT contain Company B's items
        self.assertFalse(items.filter(company=self.company_b).exists())
        clear_tenant_context()
"""
    
    return test_code


def main():
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  AUTOMATIC MODEL CONVERSION SCRIPT".center(78) + "║")
    print("║" + "  Convert models to TenantAwareManager for automatic isolation".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    # Generate report
    generate_conversion_report()
    
    # Ask user what they want to do
    print()
    print("OPTIONS:")
    print("  1) Generate conversion snippets for all models")
    print("  2) Show specific model details")
    print("  3) Generate test code for models")
    print("  4) Just show the report")
    print()
    
    choice = input("Select option (1-4): ").strip()
    
    if choice == '1':
        print("\n" + "=" * 80)
        print("CONVERSION SNIPPETS")
        print("=" * 80)
        for model_name, file_path in MODELS_TO_CONVERT:
            print(generate_conversion_code(model_name, file_path))
    
    elif choice == '2':
        model_name = input("Enter model name: ").strip()
        for name, path in MODELS_TO_CONVERT:
            if name.lower() == model_name.lower():
                print(generate_conversion_code(name, path))
                break
    
    elif choice == '3':
        print("\n" + "=" * 80)
        print("TEST CODE SNIPPETS")
        print("=" * 80)
        for model_name, _ in MODELS_TO_CONVERT:
            print(generate_test_code(model_name))
    
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("""
1. Review ISOLATION_INTEGRATION_GUIDE.md for complete documentation
2. For each model conversion:
   a. Add 'objects = TenantAwareManager()' to model
   b. Create migration: python manage.py makemigrations
   c. Apply migration: python manage.py migrate
   d. Remove manual 'company=company' filters from views
   e. Run isolation tests
3. Deploy to staging and monitor AuditLog for violations
4. Roll out to production with monitoring enabled

Questions? Review the isolation.py and enhanced_middleware.py files.
""")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
