"""
Fix cross-company marketer assignments
Run: python fix_cross_company_assignments.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser, MarketerUser, Company

def fix_cross_company_assignments():
    print("=" * 70)
    print("🔧 FIXING CROSS-COMPANY MARKETER ASSIGNMENTS")
    print("=" * 70)
    
    companies = list(Company.objects.all())
    
    for company in companies:
        print(f"\n🏢 Checking {company.company_name}...")
        
        clients = ClientUser.objects.filter(company_profile=company).select_related('assigned_marketer', 'assigned_marketer__company_profile')
        
        for client in clients:
            if client.assigned_marketer:
                marketer = client.assigned_marketer
                marketer_company = marketer.company_profile
                
                # Check if marketer is from different company
                if marketer_company and marketer_company.id != company.id:
                    print(f"\n   ⚠️  CROSS-COMPANY ASSIGNMENT DETECTED:")
                    print(f"      Client: {client.company_user_id} ({client.full_name})")
                    print(f"      Client's Company: {company.company_name}")
                    print(f"      Assigned Marketer: {marketer.company_user_id} ({marketer.full_name})")
                    print(f"      Marketer's Company: {marketer_company.company_name}")
                    
                    # Find the correct marketer in the client's company
                    correct_marketer = MarketerUser.objects.filter(
                        email=marketer.email,
                        company_profile=company
                    ).first()
                    
                    if correct_marketer:
                        print(f"      ✅ Found correct marketer in {company.company_name}: {correct_marketer.company_user_id}")
                        print(f"      🔧 Updating assignment...")
                        
                        client.assigned_marketer = correct_marketer
                        client.save(update_fields=['assigned_marketer'])
                        
                        print(f"      ✅ FIXED: Now assigned to {correct_marketer.company_user_id}")
                    else:
                        print(f"      ❌ No matching marketer found in {company.company_name}")
                        print(f"      Consider unassigning or assigning to a different marketer")
    
    print("\n" + "=" * 70)
    print("✅ CROSS-COMPANY ASSIGNMENT FIX COMPLETE")
    print("=" * 70)
    
    # Verify all assignments are now within same company
    print("\n🔍 VERIFICATION:")
    print("=" * 70)
    
    all_ok = True
    
    for company in companies:
        print(f"\n🏢 {company.company_name}:")
        clients = ClientUser.objects.filter(company_profile=company).select_related('assigned_marketer', 'assigned_marketer__company_profile')
        
        for client in clients:
            if client.assigned_marketer:
                marketer = client.assigned_marketer
                marketer_company = marketer.company_profile
                
                if marketer_company and marketer_company.id == company.id:
                    print(f"   ✅ {client.company_user_id} ({client.full_name}) → {marketer.company_user_id} ({marketer.full_name})")
                else:
                    print(f"   ❌ {client.company_user_id} ({client.full_name}) → CROSS-COMPANY ISSUE!")
                    all_ok = False
            else:
                print(f"   ⚠️  {client.company_user_id} ({client.full_name}) → NOT ASSIGNED")
    
    print("\n" + "=" * 70)
    if all_ok:
        print("🔒 STATUS: ✅ ALL ASSIGNMENTS ARE WITHIN SAME COMPANY")
    else:
        print("⚠️  STATUS: SOME ISSUES REMAIN")
    print("=" * 70)

if __name__ == '__main__':
    fix_cross_company_assignments()
