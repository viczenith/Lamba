"""
Test script to verify data isolation and company-specific IDs
Run: python test_data_isolation.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser, MarketerUser, Company

def test_data_isolation():
    print("=" * 70)
    print("🔒 DATA ISOLATION & SECURITY TEST")
    print("=" * 70)
    
    companies = Company.objects.all()
    
    if companies.count() < 2:
        print("\n⚠️  WARNING: Need at least 2 companies to test cross-company isolation")
        print(f"   Currently have: {companies.count()} company(ies)")
    
    print("\n📋 COMPANY-SPECIFIC USER IDs:")
    print("-" * 70)
    
    for company in companies:
        print(f"\n🏢 {company.company_name}")
        print(f"   {'=' * (len(company.company_name) + 2)}")
        
        # Check clients
        clients = ClientUser.objects.filter(company_profile=company)
        if clients.exists():
            print(f"\n   👥 Clients ({clients.count()}):")
            for client in clients:
                print(f"      ✅ {client.company_user_id or 'NO ID'} - {client.full_name} ({client.email})")
        else:
            print(f"\n   👥 Clients: None")
        
        # Check marketers
        marketers = MarketerUser.objects.filter(company_profile=company)
        if marketers.exists():
            print(f"\n   📢 Marketers ({marketers.count()}):")
            for marketer in marketers:
                print(f"      ✅ {marketer.company_user_id or 'NO ID'} - {marketer.full_name} ({marketer.email})")
        else:
            print(f"\n   📢 Marketers: None")
    
    print("\n" + "=" * 70)
    print("🔍 MULTI-COMPANY USER DETECTION:")
    print("-" * 70)
    
    # Find users that exist in multiple companies
    from django.db.models import Count
    from estateApp.models import CustomUser
    
    multi_company_emails = (
        CustomUser.objects
        .values('email')
        .annotate(company_count=Count('company_profile', distinct=True))
        .filter(company_count__gt=1)
    )
    
    if multi_company_emails:
        print(f"\n✅ Found {multi_company_emails.count()} user(s) in multiple companies:\n")
        
        for entry in multi_company_emails:
            email = entry['email']
            company_count = entry['company_count']
            
            print(f"   📧 {email} (in {company_count} companies):")
            
            # Show all records for this email
            user_records = CustomUser.objects.filter(email=email).select_related('company_profile')
            for record in user_records:
                user_id = "NO ID"
                if hasattr(record, 'company_user_id'):
                    user_id = record.company_user_id or "NO ID"
                else:
                    # Try to get from ClientUser or MarketerUser
                    try:
                        client = ClientUser.objects.get(pk=record.pk)
                        user_id = client.company_user_id or "NO ID"
                    except ClientUser.DoesNotExist:
                        try:
                            marketer = MarketerUser.objects.get(pk=record.pk)
                            user_id = marketer.company_user_id or "NO ID"
                        except MarketerUser.DoesNotExist:
                            pass
                
                company_name = record.company_profile.company_name if record.company_profile else "NO COMPANY"
                print(f"      └─ {user_id} | {record.role} | {company_name}")
    else:
        print("\n   No users found in multiple companies yet.")
        print("   This is expected if you haven't added the same user to multiple companies.")
    
    print("\n" + "=" * 70)
    print("🔐 SECURITY VALIDATION:")
    print("-" * 70)
    
    # Validate all users have company IDs
    clients_without_id = ClientUser.objects.filter(company_user_id__isnull=True) | ClientUser.objects.filter(company_user_id='')
    marketers_without_id = MarketerUser.objects.filter(company_user_id__isnull=True) | MarketerUser.objects.filter(company_user_id='')
    
    if clients_without_id.exists():
        print(f"\n   ⚠️  WARNING: {clients_without_id.count()} clients without company_user_id")
        for client in clients_without_id:
            print(f"      - {client.full_name} ({client.email})")
    else:
        print(f"\n   ✅ All clients have company_user_id")
    
    if marketers_without_id.exists():
        print(f"\n   ⚠️  WARNING: {marketers_without_id.count()} marketers without company_user_id")
        for marketer in marketers_without_id:
            print(f"      - {marketer.full_name} ({marketer.email})")
    else:
        print(f"\n   ✅ All marketers have company_user_id")
    
    # Check for ID collisions within companies
    print(f"\n   🔍 Checking for ID collisions...")
    
    collision_found = False
    for company in companies:
        # Check client ID collisions
        client_ids = ClientUser.objects.filter(company_profile=company).values_list('company_user_id', flat=True)
        client_duplicates = [id for id in client_ids if client_ids.filter(company_user_id=id).count() > 1]
        
        if client_duplicates:
            print(f"\n   ⚠️  Client ID collision in {company.company_name}: {set(client_duplicates)}")
            collision_found = True
        
        # Check marketer ID collisions
        marketer_ids = MarketerUser.objects.filter(company_profile=company).values_list('company_user_id', flat=True)
        marketer_duplicates = [id for id in marketer_ids if marketer_ids.filter(company_user_id=id).count() > 1]
        
        if marketer_duplicates:
            print(f"\n   ⚠️  Marketer ID collision in {company.company_name}: {set(marketer_duplicates)}")
            collision_found = True
    
    if not collision_found:
        print(f"   ✅ No ID collisions detected")
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)
    
    # Summary
    total_clients = ClientUser.objects.count()
    total_marketers = MarketerUser.objects.count()
    clients_with_id = ClientUser.objects.exclude(company_user_id__isnull=True).exclude(company_user_id='').count()
    marketers_with_id = MarketerUser.objects.exclude(company_user_id__isnull=True).exclude(company_user_id='').count()
    
    print(f"\n📊 SUMMARY:")
    print(f"   Companies: {companies.count()}")
    print(f"   Clients: {clients_with_id}/{total_clients} with IDs")
    print(f"   Marketers: {marketers_with_id}/{total_marketers} with IDs")
    print(f"   Multi-company users: {multi_company_emails.count() if multi_company_emails else 0}")
    
    if clients_with_id == total_clients and marketers_with_id == total_marketers and not collision_found:
        print(f"\n🔒 STATUS: ✅ SECURE - NO DATA LEAKAGE DETECTED")
    else:
        print(f"\n⚠️  STATUS: WARNINGS DETECTED - Review above")

if __name__ == '__main__':
    test_data_isolation()
