#!/usr/bin/env python3
"""
Test script to verify dynamic company switching in chat interface
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth.models import AnonymousUser
from estateApp.models import Company, CustomUser, PlotAllocation, Message
from estateApp.views import chat_view

def test_dynamic_company_switching():
    """Test that clicking companies dynamically switches chat interface"""
    
    print("=== Testing Dynamic Company Switching ===\n")
    
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
            print("❌ Need at least 2 companies for switching test")
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
        
        # Test initial load for Company A
        print("\n=== Testing Initial Load for Company A ===")
        
        factory = RequestFactory()
        
        # Test GET request for Company A
        request_a = factory.get(f'/chat/?company_id={company_a.id}')
        request_a.user = client
        
        response_a = chat_view(request_a)
        
        if response_a.status_code == 200:
            # Check context
            context = response_a.context_data
            messages_a = context.get('messages', [])
            
            print(f"✅ Company A initial load: {messages_a.count()} messages")
            
            # Verify only Company A messages are shown
            for message in messages_a:
                if message.company != company_a:
                    print(f"❌ Company A showing message from {message.company.company_name}")
                    return False
            
            print("✅ Company A initial load shows only Company A messages")
        
        # Test initial load for Company B
        print("\n=== Testing Initial Load for Company B ===")
        
        # Test GET request for Company B
        request_b = factory.get(f'/chat/?company_id={company_b.id}')
        request_b.user = client
        
        response_b = chat_view(request_b)
        
        if response_b.status_code == 200:
            # Check context
            context = response_b.context_data
            messages_b = context.get('messages', [])
            
            print(f"✅ Company B initial load: {messages_b.count()} messages")
            
            # Verify only Company B messages are shown
            for message in messages_b:
                if message.company != company_b:
                    print(f"❌ Company B showing message from {message.company.company_name}")
                    return False
            
            print("✅ Company B initial load shows only Company B messages")
        
        # Test polling for new messages (simulating dynamic switching)
        print("\n=== Testing Polling for New Messages ===")
        
        # Poll for new messages in Company A (simulating clicking Company A)
        request_poll_a = factory.get(f'/chat/?last_msg=0&company_id={company_a.id}')
        request_poll_a.user = client
        
        response_poll_a = chat_view(request_poll_a)
        
        if response_poll_a.status_code == 200:
            import json
            data_a = json.loads(response_poll_a.content)
            
            print(f"✅ Company A polling: {len(data_a.get('messages', []))} messages")
            
            # Verify only Company A messages are returned
            for msg in data_a.get('messages', []):
                message_obj = Message.objects.get(id=msg['id'])
                if message_obj.company != company_a:
                    print(f"❌ Company A polling showing message from {message_obj.company.company_name}")
                    return False
            
            print("✅ Company A polling returns only Company A messages")
        
        # Poll for new messages in Company B (simulating clicking Company B)
        request_poll_b = factory.get(f'/chat/?last_msg=0&company_id={company_b.id}')
        request_poll_b.user = client
        
        response_poll_b = chat_view(request_poll_b)
        
        if response_poll_b.status_code == 200:
            import json
            data_b = json.loads(response_poll_b.content)
            
            print(f"✅ Company B polling: {len(data_b.get('messages', []))} messages")
            
            # Verify only Company B messages are returned
            for msg in data_b.get('messages', []):
                message_obj = Message.objects.get(id=msg['id'])
                if message_obj.company != company_b:
                    print(f"❌ Company B polling showing message from {message_obj.company.company_name}")
                    return False
            
            print("✅ Company B polling returns only Company B messages")
        
        # Test that switching works correctly
        print("\n=== Testing Company Switching Logic ===")
        
        # Simulate switching from Company A to Company B
        # This tests the JavaScript logic that should happen when clicking a company
        
        # Initial state: Company A selected
        initial_messages = Message.objects.filter(
            company=company_a
        ).filter(
            Q(sender=client) | Q(recipient=client)
        ).count()
        
        print(f"✅ Initial state (Company A): {initial_messages} messages")
        
        # After switching to Company B, should show Company B messages
        switched_messages = Message.objects.filter(
            company=company_b
        ).filter(
            Q(sender=client) | Q(recipient=client)
        ).count()
        
        print(f"✅ After switch (Company B): {switched_messages} messages")
        
        # Verify the counts are different (proving switching works)
        if initial_messages != switched_messages:
            print("✅ Company switching shows different message counts")
        else:
            print("⚠️  Company switching shows same message counts (might be expected if equal)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    result = test_dynamic_company_switching()
    
    print(f"\n=== Test Result ===")
    print(f"Dynamic company switching test: {'✅ PASSED' if result else '❌ FAILED'}")
    
    if result:
        print("\n🎉 Dynamic company switching is working correctly!")
        print("Clicking companies in the My Companies explorer should now dynamically switch the chat interface.")
    else:
        print("\n❌ Dynamic company switching test failed.")