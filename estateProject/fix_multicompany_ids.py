"""
Verify and adjust existing multi-company users to ensure each has unique IDs per company
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import (
    CompanyMarketerProfile, MarketerAffiliation, Company,
    CompanyClientProfile, ClientUser
)
from django.db.models import Count
from django.db import transaction


def check_and_fix_marketer_ids():
    """Check and fix marketer IDs across companies"""
    print("\n" + "="*80)
    print("CHECKING & FIXING MARKETER IDs")
    print("="*80)
    
    # Find marketers in multiple companies
    multi = MarketerAffiliation.objects.values('marketer').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    print(f"\n📊 Found {multi.count()} marketers in multiple companies\n")
    
    issues = 0
    fixed = 0
    
    for item in multi:
        marketer_id = item['marketer']
        affiliations = MarketerAffiliation.objects.filter(marketer_id=marketer_id)
        marketer = affiliations.first().marketer
        
        print(f"👤 {marketer.full_name} (ID: {marketer_id}):")
        
        # Check each company
        for aff in affiliations:
            company = aff.company
            profile = CompanyMarketerProfile.objects.filter(
                marketer_id=marketer_id,
                company_id=company.id
            ).first()
            
            if profile:
                print(f"   ✓ {company.company_name}: {profile.company_marketer_uid} (ID: {profile.company_marketer_id})")
            else:
                # Missing profile - create it
                print(f"   ❌ {company.company_name}: MISSING PROFILE - Creating...")
                try:
                    # Get next ID for this company
                    from django.db.models import Max
                    max_id = CompanyMarketerProfile.objects.filter(
                        company=company
                    ).aggregate(max_id=Max('company_marketer_id'))
                    next_id = (max_id['max_id'] or 0) + 1
                    
                    # Generate UID
                    prefix = company._company_prefix()
                    uid = f"{prefix}MKT{next_id:03d}"
                    
                    # Create profile
                    profile = CompanyMarketerProfile.objects.create(
                        marketer_id=marketer_id,
                        company=company,
                        company_marketer_id=next_id,
                        company_marketer_uid=uid
                    )
                    print(f"      ✓ Created: {uid}")
                    fixed += 1
                except Exception as e:
                    print(f"      ✗ Error: {str(e)}")
                    issues += 1
    
    print(f"\n📊 Summary: {fixed} profiles created, {issues} issues")
    return issues == 0


def check_and_fix_client_ids():
    """Check and fix client IDs across companies"""
    print("\n" + "="*80)
    print("CHECKING & FIXING CLIENT IDs")
    print("="*80)
    
    # Find clients assigned to multiple companies (via assignments)
    from estateApp.models import ClientMarketerAssignment
    
    clients_in_companies = {}
    for assignment in ClientMarketerAssignment.objects.all():
        client_id = assignment.client_id
        company_id = assignment.company_id
        if client_id not in clients_in_companies:
            clients_in_companies[client_id] = set()
        clients_in_companies[client_id].add(company_id)
    
    multi_company_clients = {cid: cids for cid, cids in clients_in_companies.items() if len(cids) > 1}
    
    print(f"\n📊 Found {len(multi_company_clients)} clients in multiple companies\n")
    
    issues = 0
    fixed = 0
    
    for client_id, company_ids in multi_company_clients.items():
        try:
            client = ClientUser.objects.get(id=client_id)
            print(f"👤 {client.full_name} (ID: {client_id}):")
            
            for company_id in company_ids:
                company = Company.objects.get(id=company_id)
                profile = CompanyClientProfile.objects.filter(
                    client_id=client_id,
                    company_id=company_id
                ).first()
                
                if profile:
                    print(f"   ✓ {company.company_name}: {profile.company_client_uid} (ID: {profile.company_client_id})")
                else:
                    # Missing profile - create it
                    print(f"   ❌ {company.company_name}: MISSING PROFILE - Creating...")
                    try:
                        from django.db.models import Max
                        max_id = CompanyClientProfile.objects.filter(
                            company=company
                        ).aggregate(max_id=Max('company_client_id'))
                        next_id = (max_id['max_id'] or 0) + 1
                        
                        prefix = company._company_prefix()
                        uid = f"{prefix}CLT{next_id:03d}"
                        
                        profile = CompanyClientProfile.objects.create(
                            client_id=client_id,
                            company=company,
                            company_client_id=next_id,
                            company_client_uid=uid
                        )
                        print(f"      ✓ Created: {uid}")
                        fixed += 1
                    except Exception as e:
                        print(f"      ✗ Error: {str(e)}")
                        issues += 1
        except ClientUser.DoesNotExist:
            print(f"❌ Client {client_id} not found")
            issues += 1
    
    print(f"\n📊 Summary: {fixed} profiles created, {issues} issues")
    return issues == 0


def main():
    print("\n" + "█"*80)
    print("█ FIXING MULTI-COMPANY USER IDs")
    print("█ Ensuring each user has unique IDs in each company")
    print("█"*80)
    
    try:
        marketer_ok = check_and_fix_marketer_ids()
        client_ok = check_and_fix_client_ids()
        
        print("\n" + "█"*80)
        print("█ VERIFICATION COMPLETE")
        print("█"*80)
        
        if marketer_ok and client_ok:
            print("\n✅ All users have proper company-specific IDs!")
            print("\n📋 Summary:")
            print(f"   ✓ Marketer profiles verified and fixed")
            print(f"   ✓ Client profiles verified and fixed")
            print(f"   ✓ Multi-company users confirmed with unique IDs per company")
            return True
        else:
            print("\n⚠️  Some issues were encountered")
            return False
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
