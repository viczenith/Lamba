#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from estateApp.models import Company, CustomUser, MarketerAffiliation, ClientMarketerAssignment

# Get Lamba Real Homes company
try:
    company = Company.objects.get(company_name='Lamba Real Homes')
    print(f"\n{'='*80}")
    print(f"LAMBA REAL HOMES - Users Report")
    print(f"{'='*80}\n")
    
    # Get all marketers affiliated with this company
    print("MARKETERS:")
    print("-" * 80)
    marketers = MarketerAffiliation.objects.filter(company=company).select_related('marketer')
    if marketers.exists():
        for idx, affiliation in enumerate(marketers, 1):
            marketer = affiliation.marketer
            print(f"{idx}. Email: {marketer.email}")
            print(f"   Name: {marketer.full_name}")
            print(f"   ID: {marketer.id}")
            print(f"   Role: {marketer.role}")
            print()
    else:
        print("No marketers found.\n")
    
    # Get all clients affiliated with this company
    print("\nCLIENTS:")
    print("-" * 80)
    clients_assignments = ClientMarketerAssignment.objects.filter(company=company).select_related('client', 'marketer')
    # Get unique clients (use dict to avoid duplicates)
    unique_clients = {}
    for assignment in clients_assignments:
        if assignment.client.id not in unique_clients:
            unique_clients[assignment.client.id] = assignment
    clients = list(unique_clients.values())
    if clients:
        for idx, assignment in enumerate(clients, 1):
            client = assignment.client
            marketer = assignment.marketer
            print(f"{idx}. Email: {client.email}")
            print(f"   Name: {client.full_name}")
            print(f"   ID: {client.id}")
            print(f"   Role: {client.role}")
            print(f"   Assigned Marketer: {marketer.email} ({marketer.full_name})")
            print()
    else:
        print("No clients found.\n")
    
    # Summary
    marketer_count = marketers.count()
    client_count = len(clients)
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total Marketers: {marketer_count}")
    print(f"Total Clients: {client_count}")
    print(f"Total Users: {marketer_count + client_count}")
    print(f"{'='*80}\n")
    
except Company.DoesNotExist:
    print("Company 'Lamba Real Homes' not found!")
    sys.exit(1)
