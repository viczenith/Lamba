"""
Script to investigate and restore missing users across companies
Run: python investigate_missing_users.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser, MarketerUser, Company
from django.contrib.auth.hashers import make_password

def investigate_and_restore():
    print("=" * 70)
    print("🔍 INVESTIGATING MISSING USERS")
    print("=" * 70)
    
    # Get both companies
    companies = Company.objects.all()
    
    if companies.count() < 2:
        print("\n⚠️  Need at least 2 companies")
        return
    
    company_a = companies[0]  # Lamba Real Homes
    company_b = companies[1]  # Lamba Properties Limited
    
    print(f"\n🏢 Company A: {company_a.company_name}")
    print(f"🏢 Company B: {company_b.company_name}")
    
    print("\n" + "=" * 70)
    print("📋 CURRENT USER DISTRIBUTION")
    print("=" * 70)
    
    # Check clients
    clients_a = ClientUser.objects.filter(company_profile=company_a)
    clients_b = ClientUser.objects.filter(company_profile=company_b)
    
    print(f"\n👥 CLIENTS:")
    print(f"   Company A ({company_a.company_name}): {clients_a.count()}")
    for client in clients_a:
        print(f"      - {client.company_user_id} | {client.full_name} | {client.email}")
    
    print(f"\n   Company B ({company_b.company_name}): {clients_b.count()}")
    for client in clients_b:
        print(f"      - {client.company_user_id} | {client.full_name} | {client.email}")
    
    # Check marketers
    marketers_a = MarketerUser.objects.filter(company_profile=company_a)
    marketers_b = MarketerUser.objects.filter(company_profile=company_b)
    
    print(f"\n📢 MARKETERS:")
    print(f"   Company A ({company_a.company_name}): {marketers_a.count()}")
    for marketer in marketers_a:
        print(f"      - {marketer.company_user_id} | {marketer.full_name} | {marketer.email}")
    
    print(f"\n   Company B ({company_b.company_name}): {marketers_b.count()}")
    for marketer in marketers_b:
        print(f"      - {marketer.company_user_id} | {marketer.full_name} | {marketer.email}")
    
    print("\n" + "=" * 70)
    print("🔄 RESTORATION ANALYSIS")
    print("=" * 70)
    
    # Based on the user's description:
    # 1. A client was in Company A, got copied to Company B, but disappeared from Company A
    # 2. Marketers were in Company B, got copied to Company A, but disappeared from Company B
    
    print("\n📝 User's Report:")
    print("   1. Client copied from Company A → Company B (now missing from A)")
    print("   2. Marketers copied from Company B → Company A (now missing from B)")
    
    # Find the client that exists only in Company B but should also be in Company A
    print("\n🔍 Looking for client email 'victorgodwinakor@gmail.com'...")
    
    # Check if this email exists as a client in Company B
    client_in_b = ClientUser.objects.filter(email='victorgodwinakor@gmail.com', company_profile=company_b).first()
    
    if client_in_b:
        print(f"\n   ✅ Found in Company B: {client_in_b.full_name} ({client_in_b.company_user_id})")
        
        # Check if also exists as marketer in Company A
        marketer_in_a = MarketerUser.objects.filter(email='victorgodwinakor@gmail.com', company_profile=company_a).first()
        
        if marketer_in_a:
            print(f"   ✅ Also exists as Marketer in Company A: {marketer_in_a.company_user_id}")
            print(f"\n   📌 This user should ALSO be a Client in Company A (currently missing)")
            
            # Ask if we should restore
            print("\n" + "=" * 70)
            print("🔧 RESTORATION NEEDED")
            print("=" * 70)
            
            print(f"\n   Will create CLIENT record in Company A:")
            print(f"      Email: {client_in_b.email}")
            print(f"      Name: {client_in_b.full_name}")
            print(f"      Phone: {client_in_b.phone}")
            print(f"      Address: {client_in_b.address}")
            
            # Generate ID for Company A
            existing_clients_a = ClientUser.objects.filter(company_profile=company_a).count()
            company_words = company_a.company_name.split()
            company_code = ''.join([word[0].upper() for word in company_words if word])[:3]
            new_client_id = f"CLT-{company_code}-{existing_clients_a + 1:04d}"
            
            print(f"      New Company A ID: {new_client_id}")
            
            response = input("\n   Restore this client to Company A? (yes/no): ").strip().lower()
            
            if response == 'yes':
                # Create new client record in Company A
                new_client = ClientUser(
                    email=client_in_b.email,
                    full_name=client_in_b.full_name,
                    address=client_in_b.address,
                    phone=client_in_b.phone,
                    date_of_birth=client_in_b.date_of_birth,
                    country=client_in_b.country,
                    company_profile=company_a,
                    about=client_in_b.about,
                    job=client_in_b.job,
                    profile_image=client_in_b.profile_image,
                    company_user_id=new_client_id,
                    assigned_marketer=None,  # Will be assigned later if needed
                )
                new_client.password = client_in_b.password  # Copy password hash
                new_client.save()
                
                print(f"\n   ✅ CLIENT RESTORED to Company A!")
                print(f"      ID: {new_client.company_user_id}")
                print(f"      Name: {new_client.full_name}")
                print(f"      Email: {new_client.email}")
            else:
                print("\n   ⏭️  Restoration skipped")
    
    # Now check for marketers that should be in Company B
    print("\n" + "=" * 70)
    print("🔍 CHECKING FOR MARKETERS TO RESTORE TO COMPANY B")
    print("=" * 70)
    
    # Find marketers in Company A that might need to be restored to Company B
    marketers_to_check = ['viczenithgodwin@gmail.com', 'victrzenith@gmail.com']
    
    for email in marketers_to_check:
        marketer_in_a = MarketerUser.objects.filter(email=email, company_profile=company_a).first()
        
        if marketer_in_a:
            print(f"\n   📧 Checking: {email}")
            print(f"      Found in Company A: {marketer_in_a.full_name} ({marketer_in_a.company_user_id})")
            
            # Check if exists in Company B
            marketer_in_b = MarketerUser.objects.filter(email=email, company_profile=company_b).first()
            
            if not marketer_in_b:
                print(f"      ⚠️  NOT found in Company B - needs restoration")
                
                # Generate ID for Company B
                existing_marketers_b = MarketerUser.objects.filter(company_profile=company_b).count()
                company_words = company_b.company_name.split()
                company_code = ''.join([word[0].upper() for word in company_words if word])[:3]
                new_marketer_id = f"MKT-{company_code}-{existing_marketers_b + 1:04d}"
                
                print(f"      New Company B ID: {new_marketer_id}")
                
                response = input(f"\n   Restore {marketer_in_a.full_name} to Company B? (yes/no): ").strip().lower()
                
                if response == 'yes':
                    # Create new marketer record in Company B
                    new_marketer = MarketerUser(
                        email=marketer_in_a.email,
                        full_name=marketer_in_a.full_name,
                        address=marketer_in_a.address,
                        phone=marketer_in_a.phone,
                        date_of_birth=marketer_in_a.date_of_birth,
                        country=marketer_in_a.country,
                        company_profile=company_b,
                        about=marketer_in_a.about,
                        job=marketer_in_a.job,
                        profile_image=marketer_in_a.profile_image,
                        company_user_id=new_marketer_id,
                    )
                    new_marketer.password = marketer_in_a.password  # Copy password hash
                    new_marketer.save()
                    
                    print(f"\n   ✅ MARKETER RESTORED to Company B!")
                    print(f"      ID: {new_marketer.company_user_id}")
                    print(f"      Name: {new_marketer.full_name}")
                    print(f"      Email: {new_marketer.email}")
                else:
                    print("\n   ⏭️  Restoration skipped")
            else:
                print(f"      ✅ Already exists in Company B: {marketer_in_b.company_user_id}")
    
    print("\n" + "=" * 70)
    print("✅ INVESTIGATION COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    investigate_and_restore()
