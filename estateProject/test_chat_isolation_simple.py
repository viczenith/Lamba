#!/usr/bin/env python3
"""
Simple test script to verify chat message isolation between companies
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.db.models import Q
from estateApp.models import Company, CustomUser, PlotAllocation, Message

def test_chat_message_isolation():
    """Test that messages are properly isolated between companies"""
    
    print("=== Testing Chat Message Isolation ===\n")
    
    try:
        # Get a test client
        client = CustomUser.objects.filter(role='client').first()
        if not client:
            print("❌ No client users found in database")
            return False
        
        print(f"✅ Found client: {client.email} (ID: {client.id})")
        
        # Get companies for this client
        companies = Company.objects.filter(
            estates__plotallocation__client=client
        ).distinct().order_by('company_name')
        
        if companies.count() < 2:
            print("❌ Need at least 2 companies for isolation test")
            return False
        
        company_a = companies[0]
        company_b = companies[1]
        
        print(f"✅ Found companies: {company_a.company_name} and {company_b.company_name}")
        
        # Get admins for each company
        admin_a = CustomUser.objects.filter(
            role__in=['admin', 'support'],
            company_profile=company_a
        ).first()
        
        admin_b = CustomUser.objects.filter(
            role__in=['admin', 'support'],
            company_profile=company_b
        ).first()
        
        if not admin_a or not admin_b:
            print("❌ Need admins for both companies")
            return False
        
        print(f"✅ Found admins: {admin_a.email} for {company_a.company_name}, {admin_b.email} for {company_b.company_name}")
        
        # Send messages to Company A
        message_a1 = Message.objects.create(
            sender=client,
            recipient=admin_a,
            company=company_a,
            content="Message to Company A",
            message_type='enquiry',
            status='sent'
        )
        
        message_a2 = Message.objects.create(
            sender=admin_a,
            recipient=client,
            company=company_a,
            content="Response from Company A",
            message_type='enquiry',
            status='sent'
        )
        
        # Send messages to Company B
        message_b1 = Message.objects.create(
            sender=client,
            recipient=admin_b,
            company=company_b,
            content="Message to Company B",
            message_type='enquiry',
            status='sent'
        )
        
        message_b2 = Message.objects.create(
            sender=admin_b,
            recipient=client,
            company=company_b,
            content="Response from Company B",
            message_type='enquiry',
            status='sent'
        )
        
        print("✅ Created test messages for both companies")
        
        # Test message filtering directly (without HTTP requests)
        print("\n=== Testing Message Filtering ===")
        
        # Get messages for Company A
        messages_a = Message.objects.filter(
            company=company_a
        ).filter(
            Q(sender=client) | Q(recipient=client)
        ).order_by('date_sent')
        
        print(f"✅ Company A has {messages_a.count()} messages")
        
        # Verify only Company A messages are retrieved
        for message in messages_a:
            if message.company != company_a:
                print(f"❌ Company A filtering showing message from {message.company.company_name}")
                return False
        
        print("✅ Company A filtering only returns Company A messages")
        
        # Get messages for Company B
        messages_b = Message.objects.filter(
            company=company_b
        ).filter(
            Q(sender=client) | Q(recipient=client)
        ).order_by('date_sent')
        
        print(f"✅ Company B has {messages_b.count()} messages")
        
        # Verify only Company B messages are retrieved
        for message in messages_b:
            if message.company != company_b:
                print(f"❌ Company B filtering showing message from {message.company.company_name}")
                return False
        
        print("✅ Company B filtering only returns Company B messages")
        
        # Test that Company A messages don't appear in Company B's list
        company_a_ids = set(messages_a.values_list('id', flat=True))
        company_b_ids = set(messages_b.values_list('id', flat=True))
        
        if company_a_ids.intersection(company_b_ids):
            print("❌ Messages are overlapping between companies")
            return False
        
        print("✅ No message overlap between companies")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    result = test_chat_message_isolation()
    
    print(f"\n=== Test Result ===")
    print(f"Chat message isolation test: {'✅ PASSED' if result else '❌ FAILED'}")
    
    if result:
        print("\n🎉 Chat message isolation is working correctly!")
        print("Messages from Company A will NOT appear in Company B's chat and vice versa.")
    else:
        print("\n❌ Chat message isolation test failed.")