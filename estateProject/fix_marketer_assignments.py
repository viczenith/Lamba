"""
Script to investigate and restore marketer assignments
Run: python fix_marketer_assignments.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser, MarketerUser, Company

def fix_marketer_assignments():
    print("=" * 70)
    print("🔍 INVESTIGATING MARKETER ASSIGNMENTS")
    print("=" * 70)
    
    # Get companies
    companies = list(Company.objects.all())
    
    for company in companies:
        print(f"\n🏢 {company.company_name}")
        print("=" * 70)
        
        clients = ClientUser.objects.filter(company_profile=company)
        marketers = MarketerUser.objects.filter(company_profile=company)
        
        print(f"\n📊 Available Marketers in {company.company_name}:")
        if marketers.exists():
            for idx, marketer in enumerate(marketers, 1):
                print(f"   {idx}. {marketer.company_user_id} - {marketer.full_name} ({marketer.email})")
        else:
            print("   No marketers available")
        
        print(f"\n👥 Clients in {company.company_name}:")
        if clients.exists():
            for client in clients:
                if client.assigned_marketer:
                    print(f"   ✅ {client.company_user_id} - {client.full_name}")
                    print(f"      Assigned to: {client.assigned_marketer.full_name} ({client.assigned_marketer.company_user_id})")
                else:
                    print(f"   ⚠️  {client.company_user_id} - {client.full_name}")
                    print(f"      Status: NOT ASSIGNED")
                    
                    # Try to find if this email has a marketer assignment in another company record
                    other_client_records = ClientUser.objects.filter(
                        email=client.email
                    ).exclude(pk=client.pk).select_related('assigned_marketer')
                    
                    if other_client_records.exists():
                        print(f"      🔍 Checking other company records for this email...")
                        for other_client in other_client_records:
                            if other_client.assigned_marketer:
                                other_company = other_client.company_profile.company_name if other_client.company_profile else "Unknown"
                                print(f"         Found assignment in {other_company}: {other_client.assigned_marketer.full_name}")
                                
                                # Check if same marketer exists in current company
                                marketer_email = other_client.assigned_marketer.email
                                matching_marketer = MarketerUser.objects.filter(
                                    email=marketer_email,
                                    company_profile=company
                                ).first()
                                
                                if matching_marketer:
                                    print(f"         ✅ Same marketer exists in {company.company_name}: {matching_marketer.company_user_id}")
                                    print(f"         🔧 Restoring assignment...")
                                    
                                    client.assigned_marketer = matching_marketer
                                    client.save(update_fields=['assigned_marketer'])
                                    
                                    print(f"         ✅ RESTORED: {client.full_name} → {matching_marketer.full_name}")
                                else:
                                    print(f"         ⚠️  Marketer {other_client.assigned_marketer.full_name} not found in {company.company_name}")
        else:
            print("   No clients found")
    
    print("\n" + "=" * 70)
    print("✅ ASSIGNMENT CHECK COMPLETE")
    print("=" * 70)
    
    # Show final state
    print("\n📊 FINAL MARKETER ASSIGNMENTS:")
    print("=" * 70)
    
    for company in companies:
        print(f"\n🏢 {company.company_name}:")
        clients = ClientUser.objects.filter(company_profile=company)
        
        assigned_count = clients.filter(assigned_marketer__isnull=False).count()
        unassigned_count = clients.filter(assigned_marketer__isnull=True).count()
        
        print(f"   ✅ Assigned: {assigned_count}")
        print(f"   ⚠️  Unassigned: {unassigned_count}")
        
        for client in clients:
            if client.assigned_marketer:
                print(f"      • {client.company_user_id} ({client.full_name}) → {client.assigned_marketer.company_user_id} ({client.assigned_marketer.full_name})")
            else:
                print(f"      • {client.company_user_id} ({client.full_name}) → NOT ASSIGNED")

if __name__ == '__main__':
    fix_marketer_assignments()
