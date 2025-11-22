"""
Script to investigate and restore users that were moved between companies
Run: python investigate_and_restore_users.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser, MarketerUser, Company
from django.db.models import Count

def investigate_and_restore():
    print("=" * 70)
    print("🔍 INVESTIGATING MOVED USERS")
    print("=" * 70)
    
    # Get companies
    companies = list(Company.objects.all())
    if len(companies) < 2:
        print("\n⚠️  Need at least 2 companies to investigate cross-company moves")
        return
    
    company_a = companies[0]  # First company (likely Lamba Real Homes)
    company_b = companies[1]  # Second company (likely Lamba Properties Limited)
    
    print(f"\n🏢 Company A: {company_a.company_name}")
    print(f"🏢 Company B: {company_b.company_name}")
    
    print("\n" + "=" * 70)
    print("📊 CURRENT STATE")
    print("=" * 70)
    
    # Show current clients
    clients_a = ClientUser.objects.filter(company_profile=company_a)
    clients_b = ClientUser.objects.filter(company_profile=company_b)
    
    print(f"\n👥 Clients in {company_a.company_name}: {clients_a.count()}")
    for client in clients_a:
        print(f"   - {client.company_user_id} | {client.full_name} ({client.email})")
    
    print(f"\n👥 Clients in {company_b.company_name}: {clients_b.count()}")
    for client in clients_b:
        print(f"   - {client.company_user_id} | {client.full_name} ({client.email})")
    
    # Show current marketers
    marketers_a = MarketerUser.objects.filter(company_profile=company_a)
    marketers_b = MarketerUser.objects.filter(company_profile=company_b)
    
    print(f"\n📢 Marketers in {company_a.company_name}: {marketers_a.count()}")
    for marketer in marketers_a:
        print(f"   - {marketer.company_user_id} | {marketer.full_name} ({marketer.email})")
    
    print(f"\n📢 Marketers in {company_b.company_name}: {marketers_b.count()}")
    for marketer in marketers_b:
        print(f"   - {marketer.company_user_id} | {marketer.full_name} ({marketer.email})")
    
    print("\n" + "=" * 70)
    print("🔍 DETECTING MOVED USERS")
    print("=" * 70)
    
    # Find emails that should be in both companies but aren't
    print("\n📧 Checking for users that might have been moved...")
    
    # Get all unique emails across both companies
    all_emails = set()
    for client in ClientUser.objects.filter(company_profile__in=[company_a, company_b]):
        all_emails.add(client.email)
    for marketer in MarketerUser.objects.filter(company_profile__in=[company_a, company_b]):
        all_emails.add(marketer.email)
    
    moved_users = []
    
    for email in all_emails:
        # Check if this email exists in only one company
        client_a_exists = ClientUser.objects.filter(email=email, company_profile=company_a).exists()
        client_b_exists = ClientUser.objects.filter(email=email, company_profile=company_b).exists()
        marketer_a_exists = MarketerUser.objects.filter(email=email, company_profile=company_a).exists()
        marketer_b_exists = MarketerUser.objects.filter(email=email, company_profile=company_b).exists()
        
        # Detect potential moves
        if client_b_exists and not client_a_exists:
            # Client might have been moved from A to B
            client = ClientUser.objects.get(email=email, company_profile=company_b)
            print(f"\n⚠️  POTENTIAL MOVE DETECTED:")
            print(f"   Client: {client.full_name} ({email})")
            print(f"   Current location: {company_b.company_name}")
            print(f"   Missing from: {company_a.company_name}")
            moved_users.append({
                'type': 'client',
                'user': client,
                'from_company': company_a,
                'to_company': company_b
            })
        
        if marketer_a_exists and not marketer_b_exists:
            # Marketer might have been moved from B to A
            marketer = MarketerUser.objects.get(email=email, company_profile=company_a)
            print(f"\n⚠️  POTENTIAL MOVE DETECTED:")
            print(f"   Marketer: {marketer.full_name} ({email})")
            print(f"   Current location: {company_a.company_name}")
            print(f"   Missing from: {company_b.company_name}")
            moved_users.append({
                'type': 'marketer',
                'user': marketer,
                'from_company': company_b,
                'to_company': company_a
            })
    
    if not moved_users:
        print("\n✅ No moved users detected. Users might already be restored or never moved.")
        return
    
    print("\n" + "=" * 70)
    print("🔧 RESTORATION OPTIONS")
    print("=" * 70)
    
    print(f"\n📋 Found {len(moved_users)} user(s) that need restoration:")
    for idx, item in enumerate(moved_users, 1):
        user = item['user']
        print(f"\n{idx}. {item['type'].upper()}: {user.full_name} ({user.email})")
        print(f"   Currently in: {item['to_company'].company_name}")
        print(f"   Should also be in: {item['from_company'].company_name}")
    
    print("\n" + "=" * 70)
    print("💾 RESTORING USERS")
    print("=" * 70)
    
    for item in moved_users:
        user = item['user']
        from_company = item['from_company']
        user_type = item['type']
        
        print(f"\n🔄 Restoring {user.full_name} to {from_company.company_name}...")
        
        try:
            if user_type == 'client':
                # Create new client record in the missing company
                new_client = ClientUser(
                    email=user.email,
                    full_name=user.full_name,
                    address=user.address,
                    phone=user.phone,
                    date_of_birth=user.date_of_birth,
                    country=user.country,
                    company_profile=from_company,
                    assigned_marketer=None,  # Will need to be reassigned
                    last_login=user.last_login,
                    is_superuser=user.is_superuser,
                    is_staff=user.is_staff,
                    is_active=user.is_active,
                    date_joined=user.date_joined,
                    date_registered=user.date_registered,
                    about=user.about,
                    job=user.job,
                    profile_image=user.profile_image,
                )
                new_client.password = user.password
                new_client.save()
                print(f"   ✅ Created client record: {new_client.company_user_id}")
                
            elif user_type == 'marketer':
                # Create new marketer record in the missing company
                new_marketer = MarketerUser(
                    email=user.email,
                    full_name=user.full_name,
                    address=user.address,
                    phone=user.phone,
                    date_of_birth=user.date_of_birth,
                    country=user.country,
                    company_profile=from_company,
                    last_login=user.last_login,
                    is_superuser=user.is_superuser,
                    is_staff=user.is_staff,
                    is_active=user.is_active,
                    date_joined=user.date_joined,
                    date_registered=user.date_registered,
                    about=user.about,
                    job=user.job,
                    profile_image=user.profile_image,
                )
                new_marketer.password = user.password
                new_marketer.save()
                print(f"   ✅ Created marketer record: {new_marketer.company_user_id}")
        
        except Exception as e:
            print(f"   ❌ Error restoring user: {str(e)}")
    
    print("\n" + "=" * 70)
    print("✅ RESTORATION COMPLETE")
    print("=" * 70)
    
    # Show final state
    print("\n📊 FINAL STATE:")
    
    clients_a = ClientUser.objects.filter(company_profile=company_a)
    clients_b = ClientUser.objects.filter(company_profile=company_b)
    marketers_a = MarketerUser.objects.filter(company_profile=company_a)
    marketers_b = MarketerUser.objects.filter(company_profile=company_b)
    
    print(f"\n👥 Clients in {company_a.company_name}: {clients_a.count()}")
    for client in clients_a:
        print(f"   - {client.company_user_id} | {client.full_name} ({client.email})")
    
    print(f"\n👥 Clients in {company_b.company_name}: {clients_b.count()}")
    for client in clients_b:
        print(f"   - {client.company_user_id} | {client.full_name} ({client.email})")
    
    print(f"\n📢 Marketers in {company_a.company_name}: {marketers_a.count()}")
    for marketer in marketers_a:
        print(f"   - {marketer.company_user_id} | {marketer.full_name} ({marketer.email})")
    
    print(f"\n📢 Marketers in {company_b.company_name}: {marketers_b.count()}")
    for marketer in marketers_b:
        print(f"   - {marketer.company_user_id} | {marketer.full_name} ({marketer.email})")

if __name__ == '__main__':
    investigate_and_restore()
