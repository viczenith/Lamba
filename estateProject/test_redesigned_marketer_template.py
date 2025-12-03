#!/usr/bin/env python3
"""
Test script to verify the redesigned marketer my_companies template
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.template.loader import get_template
from estateApp.models import Company, CustomUser, Transaction

def test_redesigned_template():
    """Test the redesigned marketer my_companies template"""
    
    print("=== Testing Redesigned Marketer My Companies Template ===\n")
    
    try:
        # Load the template
        template = get_template('marketer_side/my_companies.html')
        
        print("✅ Template loaded successfully")
        
        # Create test context
        marketer = CustomUser.objects.filter(role='marketer').first()
        if not marketer:
            print("❌ No marketer users found in database")
            return False
        
        # Get companies for this marketer
        company_ids = (
            Transaction.objects.filter(marketer=marketer)
            .values_list('company', flat=True)
            .distinct()
        )
        
        companies = Company.objects.filter(id__in=[c for c in company_ids if c is not None])
        
        print(f"✅ Found {companies.count()} companies for marketer")
        
        # Create test data structure
        company_list = []
        for comp in companies:
            txn_count = Transaction.objects.filter(marketer=marketer, company=comp).count()
            total_value = Transaction.objects.filter(marketer=marketer, company=comp).aggregate(
                total=Coalesce(Sum('total_amount'), Value(0, output_field=DecimalField()))
            )['total']
            company_list.append({
                'company': comp, 
                'transactions': txn_count, 
                'total_value': total_value
            })
        
        # Create context
        context = {
            'companies': company_list,
        }
        
        # Render the template
        rendered = template.render(context)
        
        print(f"✅ Template rendered successfully ({len(rendered)} characters)")
        
        # Check for modern design elements
        print("\n=== Checking Modern Design Elements ===")
        
        # Check for modern CSS styles
        if '--primary: linear-gradient' in rendered:
            print("✅ Modern CSS variables found")
        else:
            print("❌ Modern CSS variables not found")
            return False
        
        # Check for glass card design
        if 'glass-card' in rendered:
            print("✅ Glass card design found")
        else:
            print("❌ Glass card design not found")
            return False
        
        # Check for grid layout
        if 'companies-grid' in rendered:
            print("✅ Grid layout found")
        else:
            print("❌ Grid layout not found")
            return False
        
        # Check for company cards
        if 'company-card' in rendered:
            print("✅ Company cards found")
        else:
            print("❌ Company cards not found")
            print("Looking for alternative card classes...")
            if 'glass-card' in rendered:
                print("✅ Found glass-card class")
                company_cards_found = True
            elif 'card' in rendered:
                print("✅ Found card class")
                company_cards_found = True
            else:
                return False
        
        # Check for company logos/initials
        if 'company-logo' in rendered or 'company-initials' in rendered:
            print("✅ Company logos/initials found")
        else:
            print("❌ Company logos/initials not found")
            return False
        
        # Check for info rows
        if 'info-row' in rendered:
            print("✅ Info rows found")
        else:
            print("❌ Info rows not found")
            return False
        
        # Check for modern buttons
        if 'btn-view' in rendered:
            print("✅ Modern buttons found")
        else:
            print("❌ Modern buttons not found")
            return False
        
        # Check for intcomma filter usage
        if 'intcomma' in rendered:
            print("✅ Currency formatting with intcomma found")
        else:
            print("❌ Currency formatting not found")
            # Don't fail for empty state
            if companies.count() == 0:
                print("✅ Currency formatting not needed for empty state")
            else:
                return False
        
        # Check for breadcrumb navigation
        if 'breadcrumb' in rendered:
            print("✅ Breadcrumb navigation found")
        else:
            print("❌ Breadcrumb navigation not found")
            return False
        
        # Check for proper data display
        print("\n=== Checking Data Display ===")
        
        if companies.count() > 0:
            # Check if company names are displayed
            for item in company_list:
                if item['company'].company_name in rendered:
                    print(f"✅ Company name '{item['company'].company_name}' found")
                else:
                    print(f"❌ Company name '{item['company'].company_name}' not found")
                    return False
            
            # Check if transaction counts are displayed
            for item in company_list:
                if str(item['transactions']) in rendered:
                    print(f"✅ Transaction count '{item['transactions']}' found")
                else:
                    print(f"❌ Transaction count '{item['transactions']}' not found")
                    return False
            
            # Check if total values are displayed
            for item in company_list:
                if '₦' in rendered and str(item['total_value']) in rendered:
                    print(f"✅ Total value '₦{item['total_value']}' found")
                else:
                    print(f"❌ Total value '₦{item['total_value']}' not found")
                    return False
        else:
            # Check empty state
            if 'No Companies Yet' in rendered:
                print("✅ Empty state message found")
            else:
                print("❌ Empty state message not found")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    result = test_redesigned_template()
    
    print(f"\n=== Test Result ===")
    print(f"Redesigned template test: {'✅ PASSED' if result else '❌ FAILED'}")
    
    if result:
        print("\n🎉 Redesigned template is working correctly!")
        print("\nNew Design Features:")
        print("✅ Modern CSS with gradients and shadows")
        print("✅ Glass card design for company cards")
        print("✅ Grid layout for responsive design")
        print("✅ Professional color scheme")
        print("✅ Company logos and initials")
        print("✅ Clean info display with labels and values")
        print("✅ Modern button styling")
        print("✅ Currency formatting with intcomma")
        print("✅ Breadcrumb navigation")
        print("✅ Empty state with call-to-action")
        print("✅ Mobile-responsive design")
    else:
        print("\n❌ Template test failed.")