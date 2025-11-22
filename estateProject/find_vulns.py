"""
Comprehensive data leakage audit script
Run: python find_vulns.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser, MarketerUser, Company, Transaction, PlotAllocation, PaymentRecord
from django.db.models import Count, Q

def audit_data_leakage():
    print("=" * 70)
    print("🔍 COMPREHENSIVE DATA LEAKAGE AUDIT")
    print("=" * 70)
    
    companies = list(Company.objects.all())
    issues_found = []
    
    print("\n1️⃣ CHECKING USER DATA ISOLATION")
    print("-" * 70)
    
    # Check for users without company assignment
    orphaned_clients = ClientUser.objects.filter(company_profile__isnull=True)
    orphaned_marketers = MarketerUser.objects.filter(company_profile__isnull=True)
    
    if orphaned_clients.exists():
        print(f"⚠️  Found {orphaned_clients.count()} clients without company assignment!")
        issues_found.append("Orphaned clients without company")
        for client in orphaned_clients:
            print(f"   - {client.full_name} ({client.email})")
    else:
        print("✅ All clients assigned to companies")
    
    if orphaned_marketers.exists():
        print(f"⚠️  Found {orphaned_marketers.count()} marketers without company assignment!")
        issues_found.append("Orphaned marketers without company")
        for marketer in orphaned_marketers:
            print(f"   - {marketer.full_name} ({marketer.email})")
    else:
        print("✅ All marketers assigned to companies")
    
    print("\n2️⃣ CHECKING CROSS-COMPANY MARKETER ASSIGNMENTS")
    print("-" * 70)
    
    cross_company_assignments = 0
    for company in companies:
        clients = ClientUser.objects.filter(
            company_profile=company
        ).select_related('assigned_marketer', 'assigned_marketer__company_profile')
        
        for client in clients:
            if client.assigned_marketer:
                marketer_company = client.assigned_marketer.company_profile
                if marketer_company and marketer_company.id != company.id:
                    print(f"⚠️  CROSS-COMPANY ASSIGNMENT:")
                    print(f"   Client: {client.company_user_id} in {company.company_name}")
                    print(f"   Assigned to: {client.assigned_marketer.company_user_id} in {marketer_company.company_name}")
                    cross_company_assignments += 1
                    issues_found.append(f"Cross-company assignment: {client.company_user_id}")
    
    if cross_company_assignments == 0:
        print("✅ No cross-company marketer assignments")
    else:
        print(f"⚠️  Found {cross_company_assignments} cross-company assignments!")
    
    print("\n3️⃣ CHECKING TRANSACTION DATA ISOLATION")
    print("-" * 70)
    
    # Check for transactions without company
    orphaned_transactions = Transaction.objects.filter(company__isnull=True)
    if orphaned_transactions.exists():
        print(f"⚠️  Found {orphaned_transactions.count()} transactions without company!")
        issues_found.append("Orphaned transactions")
    else:
        print("✅ All transactions assigned to companies")
    
    # Check for transactions with client/marketer from different company
    cross_company_transactions = 0
    for transaction in Transaction.objects.select_related('company', 'client__company_profile', 'marketer__company_profile'):
        if transaction.company:
            if transaction.client and transaction.client.company_profile:
                if transaction.client.company_profile.id != transaction.company.id:
                    print(f"⚠️  Transaction {transaction.reference_code} has client from different company!")
                    cross_company_transactions += 1
                    issues_found.append(f"Transaction {transaction.reference_code} client mismatch")
            
            if transaction.marketer and transaction.marketer.company_profile:
                if transaction.marketer.company_profile.id != transaction.company.id:
                    print(f"⚠️  Transaction {transaction.reference_code} has marketer from different company!")
                    cross_company_transactions += 1
                    issues_found.append(f"Transaction {transaction.reference_code} marketer mismatch")
    
    if cross_company_transactions == 0:
        print("✅ All transactions properly scoped to company")
    else:
        print(f"⚠️  Found {cross_company_transactions} cross-company transaction issues!")
    
    print("\n4️⃣ CHECKING PLOT ALLOCATION ISOLATION")
    print("-" * 70)
    
    cross_company_allocations = 0
    for allocation in PlotAllocation.objects.select_related('company', 'client__company_profile'):
        if allocation.company and allocation.client and allocation.client.company_profile:
            if allocation.client.company_profile.id != allocation.company.id:
                print(f"⚠️  Plot allocation has client from different company!")
                print(f"   Allocation company: {allocation.company.company_name}")
                print(f"   Client company: {allocation.client.company_profile.company_name}")
                cross_company_allocations += 1
                issues_found.append("Cross-company plot allocation")
    
    if cross_company_allocations == 0:
        print("✅ All plot allocations properly scoped")
    else:
        print(f"⚠️  Found {cross_company_allocations} cross-company allocation issues!")
    
    print("\n5️⃣ CHECKING COMPANY USER ID ASSIGNMENTS")
    print("-" * 70)
    
    clients_without_id = ClientUser.objects.filter(
        Q(company_user_id__isnull=True) | Q(company_user_id='')
    )
    marketers_without_id = MarketerUser.objects.filter(
        Q(company_user_id__isnull=True) | Q(company_user_id='')
    )
    
    if clients_without_id.exists():
        print(f"⚠️  {clients_without_id.count()} clients without company_user_id!")
        issues_found.append("Clients missing company_user_id")
    else:
        print("✅ All clients have company_user_id")
    
    if marketers_without_id.exists():
        print(f"⚠️  {marketers_without_id.count()} marketers without company_user_id!")
        issues_found.append("Marketers missing company_user_id")
    else:
        print("✅ All marketers have company_user_id")
    
    print("\n6️⃣ CHECKING ID COLLISION WITHIN COMPANIES")
    print("-" * 70)
    
    id_collisions = 0
    for company in companies:
        # Check client ID duplicates
        client_ids = ClientUser.objects.filter(
            company_profile=company
        ).values('company_user_id').annotate(count=Count('id')).filter(count__gt=1)
        
        if client_ids.exists():
            print(f"⚠️  Client ID collisions in {company.company_name}:")
            for item in client_ids:
                print(f"   ID {item['company_user_id']} appears {item['count']} times")
            id_collisions += client_ids.count()
            issues_found.append(f"Client ID collisions in {company.company_name}")
        
        # Check marketer ID duplicates
        marketer_ids = MarketerUser.objects.filter(
            company_profile=company
        ).values('company_user_id').annotate(count=Count('id')).filter(count__gt=1)
        
        if marketer_ids.exists():
            print(f"⚠️  Marketer ID collisions in {company.company_name}:")
            for item in marketer_ids:
                print(f"   ID {item['company_user_id']} appears {item['count']} times")
            id_collisions += marketer_ids.count()
            issues_found.append(f"Marketer ID collisions in {company.company_name}")
    
    if id_collisions == 0:
        print("✅ No ID collisions detected")
    else:
        print(f"⚠️  Found {id_collisions} ID collision issues!")
    
    print("\n7️⃣ CHECKING PAYMENT RECORD INTEGRITY")
    print("-" * 70)
    
    orphaned_payments = PaymentRecord.objects.filter(
        transaction__company__isnull=True
    )
    
    if orphaned_payments.exists():
        print(f"⚠️  {orphaned_payments.count()} payment records linked to transactions without company!")
        issues_found.append("Orphaned payment records")
    else:
        print("✅ All payment records properly linked")
    
    print("\n8️⃣ CHECKING EMAIL UNIQUENESS CONSTRAINTS")
    print("-" * 70)
    
    # Check for email violations (same email, same company, same role)
    duplicate_users = ClientUser.objects.values(
        'email', 'company_profile', 'role'
    ).annotate(count=Count('id')).filter(count__gt=1)
    
    if duplicate_users.exists():
        print(f"⚠️  Found {duplicate_users.count()} duplicate user violations!")
        for dup in duplicate_users:
            print(f"   Email: {dup['email']}, Company: {dup['company_profile']}, Role: {dup['role']}")
            print(f"   Count: {dup['count']} records")
        issues_found.append("Duplicate user constraint violations")
    else:
        print("✅ No duplicate user violations (same email + company + role)")
    
    print("\n" + "=" * 70)
    print("📊 AUDIT SUMMARY")
    print("=" * 70)
    
    if not issues_found:
        print("\n🔒 ✅ NO DATA LEAKAGE DETECTED!")
        print("\n   All data properly isolated:")
        print("   ✅ Users scoped to companies")
        print("   ✅ Transactions scoped to companies")
        print("   ✅ Allocations scoped to companies")
        print("   ✅ No cross-company assignments")
        print("   ✅ All users have company IDs")
        print("   ✅ No ID collisions")
        print("   ✅ No orphaned data")
        print("\n🎉 SYSTEM IS SECURE!")
    else:
        print(f"\n⚠️  FOUND {len(issues_found)} ISSUE(S):")
        for idx, issue in enumerate(issues_found, 1):
            print(f"   {idx}. {issue}")
        print("\n⚠️  ACTION REQUIRED: Fix issues above")
    
    print("\n" + "=" * 70)
    
    # Detailed company breakdown
    print("\n📋 DETAILED COMPANY BREAKDOWN:")
    print("=" * 70)
    
    for company in companies:
        print(f"\n🏢 {company.company_name}")
        print(f"   {'=' * (len(company.company_name) + 2)}")
        
        clients = ClientUser.objects.filter(company_profile=company)
        marketers = MarketerUser.objects.filter(company_profile=company)
        transactions = Transaction.objects.filter(company=company)
        allocations = PlotAllocation.objects.filter(company=company)
        
        print(f"   👥 Clients: {clients.count()}")
        print(f"   📢 Marketers: {marketers.count()}")
        print(f"   📄 Transactions: {transactions.count()}")
        print(f"   🏗️  Plot Allocations: {allocations.count()}")
        
        # Check if all clients are assigned
        unassigned = clients.filter(assigned_marketer__isnull=True).count()
        if unassigned > 0:
            print(f"   ⚠️  {unassigned} clients without marketer assignment")
        else:
            print(f"   ✅ All clients have marketer assignments")

if __name__ == '__main__':
    audit_data_leakage()
