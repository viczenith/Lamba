#!/usr/bin/env python
"""Check for missing data in Company A"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from estateApp.models import (
    CustomUser, Estate, PlotSize, PlotNumber, PlotSizeUnits,
    PlotAllocation, EstatePlot, Message, Company, Transaction
)

def check_data():
    print("\n" + "="*80)
    print("CHECKING FOR MISSING DATA")
    print("="*80)
    
    # Get Company A
    company_a = Company.objects.filter(email='estate@gmail.com').first()
    if not company_a:
        print("❌ ERROR: Company A not found!")
        return
    
    print(f"\n✅ Company A Found: {company_a.company_name}")
    print(f"   Email: {company_a.email}")
    print(f"   ID: {company_a.id}")
    
    # Check users
    print("\n" + "-"*80)
    print("USER ACCOUNTS")
    print("-"*80)
    
    all_users = CustomUser.objects.all()
    print(f"Total users in database: {all_users.count()}")
    
    company_a_users = CustomUser.objects.filter(company_profile=company_a)
    print(f"Company A users: {company_a_users.count()}")
    
    # Break down by role
    admins = CustomUser.objects.filter(company_profile=company_a, role='admin')
    clients = CustomUser.objects.filter(company_profile=company_a, role='client')
    marketers = CustomUser.objects.filter(company_profile=company_a, role='marketer')
    support = CustomUser.objects.filter(company_profile=company_a, role='support')
    
    print(f"\nCompany A Breakdown:")
    print(f"  Admins: {admins.count()}")
    for admin in admins:
        print(f"    - {admin.email} ({admin.full_name})")
    
    print(f"\n  Clients: {clients.count()}")
    if clients.count() > 0:
        for client in clients[:5]:  # Show first 5
            print(f"    - {client.email} ({client.full_name})")
        if clients.count() > 5:
            print(f"    ... and {clients.count() - 5} more")
    else:
        print("    ⚠️ NO CLIENTS FOUND!")
    
    print(f"\n  Marketers: {marketers.count()}")
    if marketers.count() > 0:
        for marketer in marketers[:5]:
            print(f"    - {marketer.email} ({marketer.full_name})")
        if marketers.count() > 5:
            print(f"    ... and {marketers.count() - 5} more")
    else:
        print("    ⚠️ NO MARKETERS FOUND!")
    
    # Check estates
    print("\n" + "-"*80)
    print("ESTATE DATA")
    print("-"*80)
    
    estates = Estate.objects.filter(company=company_a)
    print(f"Estates: {estates.count()}")
    for estate in estates:
        print(f"  - {estate.name}")
    
    # Check allocations
    print("\n" + "-"*80)
    print("PLOT ALLOCATIONS")
    print("-"*80)
    
    allocations = PlotAllocation.objects.filter(company=company_a)
    print(f"Total Allocations: {allocations.count()}")
    
    full_allocations = PlotAllocation.objects.filter(
        company=company_a,
        payment_type='full',
        plot_number__isnull=False
    )
    print(f"Full Allocations (with plot numbers): {full_allocations.count()}")
    
    pending_allocations = PlotAllocation.objects.filter(
        company=company_a,
        payment_type='part',
        plot_number__isnull=True
    )
    print(f"Pending Allocations (reservations): {pending_allocations.count()}")
    
    if allocations.count() > 0:
        print(f"\nSample Allocations:")
        for alloc in allocations[:3]:
            client_email = alloc.client.email if alloc.client else "N/A"
            plot_num = alloc.plot_number.number if alloc.plot_number else "Reserved"
            print(f"  - Client: {client_email}, Plot: {plot_num}, Type: {alloc.payment_type}")
    
    # Check transactions
    print("\n" + "-"*80)
    print("TRANSACTIONS")
    print("-"*80)
    
    transactions = Transaction.objects.filter(company=company_a)
    print(f"Total Transactions: {transactions.count()}")
    
    if transactions.count() > 0:
        print(f"\nSample Transactions:")
        for txn in transactions[:3]:
            client_email = txn.client.email if txn.client else "N/A"
            print(f"  - Client: {client_email}, Amount: {txn.total_amount}, Date: {txn.transaction_date}")
    
    # Check messages
    print("\n" + "-"*80)
    print("MESSAGES")
    print("-"*80)
    
    messages = Message.objects.filter(company=company_a)
    print(f"Total Messages: {messages.count()}")
    
    # Check for orphaned data
    print("\n" + "-"*80)
    print("ORPHANED DATA CHECK")
    print("-"*80)
    
    orphaned_users = CustomUser.objects.filter(company_profile__isnull=True)
    print(f"Users without company: {orphaned_users.count()}")
    if orphaned_users.count() > 0:
        for user in orphaned_users:
            print(f"  ⚠️ {user.email} ({user.role}) - NO COMPANY!")
    
    orphaned_estates = Estate.objects.filter(company__isnull=True)
    print(f"Estates without company: {orphaned_estates.count()}")
    
    orphaned_allocations = PlotAllocation.objects.filter(company__isnull=True)
    print(f"Allocations without company: {orphaned_allocations.count()}")
    
    # Final summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if clients.count() == 0:
        print("❌ PROBLEM: NO CLIENTS FOUND FOR COMPANY A")
    else:
        print(f"✅ Clients: {clients.count()}")
    
    if marketers.count() == 0:
        print("❌ PROBLEM: NO MARKETERS FOUND FOR COMPANY A")
    else:
        print(f"✅ Marketers: {marketers.count()}")
    
    if allocations.count() == 0:
        print("❌ PROBLEM: NO ALLOCATIONS FOUND FOR COMPANY A")
    else:
        print(f"✅ Allocations: {allocations.count()}")
    
    if estates.count() == 0:
        print("❌ PROBLEM: NO ESTATES FOUND FOR COMPANY A")
    else:
        print(f"✅ Estates: {estates.count()}")
    
    print("\n")

if __name__ == "__main__":
    check_data()
