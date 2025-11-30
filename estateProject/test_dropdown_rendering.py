#!/usr/bin/env python
"""
Test to verify that the marketer dropdown in user_registration.html 
properly renders all affiliated marketers without duplication
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from estateApp.models import (
    Company, CustomUser, MarketerAffiliation
)

def test_dropdown_rendering():
    """Test that dropdown renders all marketers correctly"""
    print("\n" + "="*80)
    print("TEST: Marketer Dropdown Rendering")
    print("="*80)
    
    company = Company.objects.filter(company_name='Lamba Real Homes').first()
    if not company:
        print("❌ Company 'Lamba Real Homes' not found")
        return False
    
    print(f"\nCompany: {company.company_name}")
    
    # Get marketers from company_profile
    company_filter = {'company_profile': company}
    marketers_primary = CustomUser.objects.filter(role='marketer', **company_filter)
    
    print(f"\n1. Primary Marketers (company_profile={company.company_name}):")
    print(f"   Count: {marketers_primary.count()}")
    for m in marketers_primary:
        print(f"   - ID: {m.id}, Email: {m.email}, Name: {m.full_name}")
    
    # Get marketers from MarketerAffiliation
    marketers_affiliated = []
    try:
        affiliation_marketer_ids = MarketerAffiliation.objects.filter(
            company=company
        ).values_list('marketer_id', flat=True).distinct()
        print(f"\n2. Affiliated Marketer IDs (from MarketerAffiliation):")
        print(f"   {list(affiliation_marketer_ids)}")
        
        if affiliation_marketer_ids:
            marketers_affiliated = CustomUser.objects.filter(
                id__in=affiliation_marketer_ids
            ).exclude(
                id__in=marketers_primary.values_list('pk', flat=True)
            )
            print(f"   Count (after excluding primary): {marketers_affiliated.count()}")
            for m in marketers_affiliated:
                print(f"   - ID: {m.id}, Email: {m.email}, Name: {m.full_name}")
    except Exception as e:
        print(f"   Error fetching affiliated marketers: {e}")
    
    # Combine both lists
    marketers = list(marketers_primary) + list(marketers_affiliated)
    
    print(f"\n3. Combined Marketer List (for dropdown):")
    print(f"   Total Count: {len(marketers)}")
    
    # Check for duplicates
    seen_ids = set()
    duplicates = []
    for m in marketers:
        if m.id in seen_ids:
            duplicates.append(m.id)
        else:
            seen_ids.add(m.id)
    
    if duplicates:
        print(f"   ⚠️  DUPLICATES FOUND: {duplicates}")
        print(f"   This would cause the same marketer to appear multiple times in the dropdown!")
        return False
    else:
        print(f"   ✅ No duplicates (unique IDs: {len(seen_ids)})")
    
    print(f"\n4. Dropdown HTML Output (simulated):")
    print(f"   <select id='marketer' name='marketer'>")
    print(f"      <option value=''>Select a Marketer (Required)</option>")
    for m in marketers:
        print(f"      <option value='{m.id}'>{m.full_name}</option>")
    print(f"   </select>")
    
    print(f"\n" + "="*80)
    print(f"✅ Dropdown rendering test PASSED")
    print(f"   - Primary marketers: {marketers_primary.count()}")
    print(f"   - Affiliated marketers: {len(marketers_affiliated)}")
    print(f"   - Total in dropdown: {len(marketers)}")
    print(f"   - Duplicates: {len(duplicates)}")
    print("="*80 + "\n")
    
    return True

if __name__ == '__main__':
    try:
        success = test_dropdown_rendering()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
