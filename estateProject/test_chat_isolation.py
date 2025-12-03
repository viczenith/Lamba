#!/usr/bin/env python3
"""
Test script to verify chat message isolation between companies
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

def test_chat_message_isolation():
    """Test that messages are properly isolated between companies"""
    
    print("=== Testing Chat Message Isolation ===\n")
    
    try:
        # Get a test client
        client = CustomUser.objects.filter(role='client').first()
        if not client:
            print("❌ No client users found in database")
            return False
        
        print(f"✅ Found client: {client.username} (ID: {client.id})")
        
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
        
        print(f"✅ Found admins: {admin_a.username} for {company_a.company_name}, {admin_b.username} for {company_b.company_name}")
        
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
        
        # Test message retrieval for Company A
        factory = RequestFactory()
        
        # Test GET request for Company A using Django test client
        from django.test import Client as DjangoTestClient
        
        test_client = DjangoTestClient()
        test_client.force_login(client)
        
        response_a = test_client.get(f'/chat/?company_id={company_a.id}')
        
        if response_a.status_code == 200:
            # Check context from test client response
            context = response_a.context
            messages_a = context.get('messages', [])
            
            print(f"✅ Company A messages: {messages_a.count()}")
            
            # Verify only Company A messages are shown
            for message in messages_a:
                if message.company != company_a:
                    print(f"❌ Company A chat showing message from {message.company.company_name}")
                    return False
            
            print("✅ Company A chat only shows Company A messages")
        
        # Test GET request for Company B
        response_b = test_client.get(f'/chat/?company_id={company_b.id}')
        
        if response_b.status_code == 200:
            # Check context from test client response
            context = response_b.context
            messages_b = context.get('messages', [])
            
            print(f"✅ Company B messages: {messages_b.count()}")
            
            # Verify only Company B messages are shown
            for message in messages_b:
                if message.company != company_b:
                    print(f"❌ Company B chat showing message from {message.company.company_name}")
                    return False
            
            print("✅ Company B chat only shows Company B messages")
        
        # Test polling for new messages
        print("\n=== Testing Polling Isolation ===")
        
        # Poll for new messages in Company A
        request_poll_a = factory.get(f'/chat/?last_msg=0&company_id={company_a.id}')
        request_poll_a.user = client
        
        response_poll_a = chat_view(request_poll_a)
        
        if response_poll_a.status_code == 200:
            import json
            data_a = json.loads(response_poll_a.content)
            
            print(f"✅ Company A polling returned {len(data_a.get('messages', []))} messages")
            
            # Verify only Company A messages are returned
            for msg in data_a.get('messages', []):
                message_obj = Message.objects.get(id=msg['id'])
                if message_obj.company != company_a:
                    print(f"❌ Company A polling showing message from {message_obj.company.company_name}")
                    return False
            
            print("✅ Company A polling only returns Company A messages")
        
        # Poll for new messages in Company B
        request_poll_b = factory.get(f'/chat/?last_msg=0&company_id={company_b.id}')
        request_poll_b.user = client
        
        response_poll_b = chat_view(request_poll_b)
        
        if response_poll_b.status_code == 200:
            import json
            data_b = json.loads(response_poll_b.content)
            
            print(f"✅ Company B polling returned {len(data_b.get('messages', []))} messages")
            
            # Verify only Company B messages are returned
            for msg in data_b.get('messages', []):
                message_obj = Message.objects.get(id=msg['id'])
                if message_obj.company != company_b:
                    print(f"❌ Company B polling showing message from {message_obj.company.company_name}")
                    return False
            
            print("✅ Company B polling only returns Company B messages")
        
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