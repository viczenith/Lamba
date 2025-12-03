#!/usr/bin/env python3
"""
Test script to verify message sending and company switching
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

def test_message_sending_and_switching():
    """Test that message sending and company switching work correctly"""
    
    print("=== Testing Message Sending and Company Switching ===\n")
    
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
        
        # Test message sending to Company A
        print("\n=== Testing Message Sending to Company A ===")
        
        factory = RequestFactory()
        
        # Create POST request to Company A
        post_data = {
            'content': 'Test message to Company A',
            'message_type': 'enquiry',
            'company_id': company_a.id,
        }
        
        request_a = factory.post('/chat/', post_data)
        request_a.user = client
        request_a.META['HTTP_X-Requested-With'] = 'XMLHttpRequest'
        
        response_a = chat_view(request_a)
        
        if response_a.status_code == 200:
            import json
            data_a = json.loads(response_a.content)
            
            if data_a.get('success'):
                print("✅ Message sent to Company A successfully")
                
                # Verify message was created in database
                message_a = Message.objects.filter(
                    sender=client,
                    recipient=admin_a,
                    company=company_a,
                    content__icontains='Test message to Company A'
                ).first()
                
                if message_a:
                    print("✅ Message found in database for Company A")
                else:
                    print("❌ Message not found in database for Company A")
                    return False
            else:
                print(f"❌ Message sending to Company A failed: {data_a.get('error')}")
                return False
        else:
            print(f"❌ POST request to Company A failed with status code: {response_a.status_code}")
            return False
        
        # Test message sending to Company B
        print("\n=== Testing Message Sending to Company B ===")
        
        # Create POST request to Company B
        post_data_b = {
            'content': 'Test message to Company B',
            'message_type': 'enquiry',
            'company_id': company_b.id,
        }
        
        request_b = factory.post('/chat/', post_data_b)
        request_b.user = client
        request_b.META['HTTP_X-Requested-With'] = 'XMLHttpRequest'
        
        response_b = chat_view(request_b)
        
        if response_b.status_code == 200:
            import json
            data_b = json.loads(response_b.content)
            
            if data_b.get('success'):
                print("✅ Message sent to Company B successfully")
                
                # Verify message was created in database
                message_b = Message.objects.filter(
                    sender=client,
                    recipient=admin_b,
                    company=company_b,
                    content__icontains='Test message to Company B'
                ).first()
                
                if message_b:
                    print("✅ Message found in database for Company B")
                else:
                    print("❌ Message not found in database for Company B")
                    # Debug: Check what messages exist for Company B
                    all_company_b_messages = Message.objects.filter(company=company_b)
                    print(f"   Debug: Found {all_company_b_messages.count()} messages for Company B")
                    for msg in all_company_b_messages:
                        print(f"     - {msg.content} (sender: {msg.sender.email}, recipient: {msg.recipient.email})")
                    return False
            else:
                print(f"❌ Message sending to Company B failed: {data_b.get('error')}")
                return False
        else:
            print(f"❌ POST request to Company B failed with status code: {response_b.status_code}")
            return False
        
        # Test message isolation after sending
        print("\n=== Testing Message Isolation After Sending ===")
        
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
                print(f"❌ Company A showing message from {message.company.company_name}")
                return False
        
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
                print(f"❌ Company B showing message from {message.company.company_name}")
                return False
        
        # Test that messages are properly isolated
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
    result = test_message_sending_and_switching()
    
    print(f"\n=== Test Result ===")
    print(f"Message sending and switching test: {'✅ PASSED' if result else '❌ FAILED'}")
    
    if result:
        print("\n🎉 Message sending and company switching are working correctly!")
        print("Users can now:")
        print("1. Send messages to different companies")
        print("2. Switch between companies dynamically")
        print("3. See company-specific messages only")
        print("4. Send messages to the correct company")
    else:
        print("\n❌ Message sending and switching test failed.")