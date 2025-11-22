"""
Fix orphaned transactions and allocations that reference clients from wrong company
Run: python fix_orphaned_data.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser, MarketerUser, Company, Transaction, PlotAllocation

def fix_orphaned_data():
    print("=" * 70)
    print("🔧 FIXING ORPHANED TRANSACTIONS AND ALLOCATIONS")
    print("=" * 70)
    
    companies = list(Company.objects.all())
    
    print("\n1️⃣ FIXING TRANSACTIONS WITH WRONG CLIENT COMPANY")
    print("-" * 70)
    
    fixed_transactions = 0
    
    for transaction in Transaction.objects.select_related('company', 'client__company_profile'):
        if transaction.company and transaction.client and transaction.client.company_profile:
            if transaction.client.company_profile.id != transaction.company.id:
                print(f"\n⚠️  Transaction {transaction.reference_code}:")
                print(f"   Transaction company: {transaction.company.company_name}")
                print(f"   Client: {transaction.client.full_name} ({transaction.client.company_user_id})")
                print(f"   Client company: {transaction.client.company_profile.company_name}")
                
                # Find the correct client record in the transaction's company
                correct_client = ClientUser.objects.filter(
                    email=transaction.client.email,
                    company_profile=transaction.company
                ).first()
                
                if correct_client:
                    print(f"   ✅ Found correct client: {correct_client.company_user_id}")
                    transaction.client = correct_client
                    
                    # Also fix marketer if needed
                    if transaction.marketer and transaction.marketer.company_profile:
                        if transaction.marketer.company_profile.id != transaction.company.id:
                            correct_marketer = MarketerUser.objects.filter(
                                email=transaction.marketer.email,
                                company_profile=transaction.company
                            ).first()
                            
                            if correct_marketer:
                                print(f"   ✅ Also fixing marketer: {correct_marketer.company_user_id}")
                                transaction.marketer = correct_marketer
                    
                    transaction.save()
                    print(f"   ✅ FIXED!")
                    fixed_transactions += 1
                else:
                    print(f"   ❌ No matching client found in {transaction.company.company_name}")
    
    print(f"\n✅ Fixed {fixed_transactions} transactions")
    
    print("\n2️⃣ FIXING PLOT ALLOCATIONS WITH WRONG CLIENT COMPANY")
    print("-" * 70)
    
    fixed_allocations = 0
    
    for allocation in PlotAllocation.objects.select_related('company', 'client__company_profile'):
        if allocation.company and allocation.client and allocation.client.company_profile:
            if allocation.client.company_profile.id != allocation.company.id:
                print(f"\n⚠️  Plot Allocation (Plot Size: {allocation.plot_size}):")
                print(f"   Allocation company: {allocation.company.company_name}")
                print(f"   Client: {allocation.client.full_name} ({allocation.client.company_user_id})")
                print(f"   Client company: {allocation.client.company_profile.company_name}")
                
                # Find the correct client record in the allocation's company
                correct_client = ClientUser.objects.filter(
                    email=allocation.client.email,
                    company_profile=allocation.company
                ).first()
                
                if correct_client:
                    print(f"   ✅ Found correct client: {correct_client.company_user_id}")
                    allocation.client = correct_client
                    allocation.save()
                    print(f"   ✅ FIXED!")
                    fixed_allocations += 1
                else:
                    print(f"   ❌ No matching client found in {allocation.company.company_name}")
    
    print(f"\n✅ Fixed {fixed_allocations} plot allocations")
    
    print("\n" + "=" * 70)
    print("✅ ORPHANED DATA FIX COMPLETE")
    print("=" * 70)
    
    print(f"\n📊 SUMMARY:")
    print(f"   Transactions fixed: {fixed_transactions}")
    print(f"   Plot allocations fixed: {fixed_allocations}")
    print(f"   Total fixes: {fixed_transactions + fixed_allocations}")

if __name__ == '__main__':
    fix_orphaned_data()
