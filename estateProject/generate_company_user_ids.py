"""
Script to generate company_user_id for existing ClientUser and MarketerUser records
Run: python generate_company_user_ids.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser, MarketerUser, Company

def generate_ids():
    print("=" * 70)
    print("GENERATING COMPANY-SPECIFIC USER IDs")
    print("=" * 70)
    
    # Generate IDs for all clients
    companies = Company.objects.all()
    
    for company in companies:
        print(f"\n📍 Processing Company: {company.company_name}")
        
        # Generate company code from company name
        company_words = company.company_name.split()
        company_code = ''.join([word[0].upper() for word in company_words if word])[:3]
        if len(company_code) < 2:
            company_code = company.company_name[:3].upper()
        
        # Process clients
        clients = ClientUser.objects.filter(company_profile=company).order_by('id')
        print(f"   → {clients.count()} clients found")
        
        for idx, client in enumerate(clients, start=1):
            if not client.company_user_id:
                client.company_user_id = f"CLT-{company_code}-{idx:04d}"
                client.save(update_fields=['company_user_id'])
                print(f"      ✅ {client.full_name}: {client.company_user_id}")
            else:
                print(f"      ⏭️  {client.full_name}: {client.company_user_id} (already set)")
        
        # Process marketers
        marketers = MarketerUser.objects.filter(company_profile=company).order_by('id')
        print(f"   → {marketers.count()} marketers found")
        
        for idx, marketer in enumerate(marketers, start=1):
            if not marketer.company_user_id:
                marketer.company_user_id = f"MKT-{company_code}-{idx:04d}"
                marketer.save(update_fields=['company_user_id'])
                print(f"      ✅ {marketer.full_name}: {marketer.company_user_id}")
            else:
                print(f"      ⏭️  {marketer.full_name}: {marketer.company_user_id} (already set)")
    
    print("\n" + "=" * 70)
    print("✅ COMPANY ID GENERATION COMPLETE")
    print("=" * 70)
    
    # Summary
    total_clients = ClientUser.objects.exclude(company_user_id__isnull=True).exclude(company_user_id='').count()
    total_marketers = MarketerUser.objects.exclude(company_user_id__isnull=True).exclude(company_user_id='').count()
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total Clients with IDs: {total_clients}")
    print(f"   Total Marketers with IDs: {total_marketers}")

if __name__ == '__main__':
    generate_ids()
