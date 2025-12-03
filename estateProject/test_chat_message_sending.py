#!/usr/bin/env python3
"""
Test script to verify chat message sending functionality
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

def test_chat_message_sending():
    """Test that chat messages can be sent successfully"""
    
    print("=== Testing Chat Message Sending ===\n")
    
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
        
        if not companies.exists():
            print("❌ No companies found for client")
            return False
        
        print(f"✅ Found {companies.count()} companies")
        
        # Get a company admin
        selected_company = companies.first()
        admin_user = CustomUser.objects.filter(
            role__in=['admin', 'support'],
            company_profile=selected_company
        ).first()
        
        if not admin_user:
            print(f"❌ No admin found for company {selected_company.company_name}")
            return False
        
        print(f"✅ Found admin: {admin_user.username} for company {selected_company.company_name}")
        
        # Test message sending via POST request
        factory = RequestFactory()
        
        # Create POST request
        post_data = {
            'content': 'Test message from client',
            'message_type': 'enquiry',
            'company_id': selected_company.id,
        }
        
        request = factory.post('/chat/', post_data)
        request.user = client
        request.META['HTTP_X-Requested-With'] = 'XMLHttpRequest'
        
        print("\n=== Testing POST request ===")
        
        # Call the chat_view function with POST request
        response = chat_view(request)
        
        # Check if the response is successful
        if response.status_code == 200:
            # Parse JSON response
            import json
            response_data = json.loads(response.content)
            
            if response_data.get('success'):
                print("✅ Message sent successfully")
                print(f"✅ Message ID: {response_data.get('message', {}).get('id')}")
                print(f"✅ Message content: {response_data.get('message', {}).get('content')}")
                
                # Verify message was created in database
                message = Message.objects.filter(
                    sender=client,
                    recipient=admin_user,
                    company=selected_company,
                    content='Test message from client'
                ).first()
                
                if message:
                    print("✅ Message found in database")
                    return True
                else:
                    print("❌ Message not found in database")
                    return False
            else:
                print(f"❌ Message sending failed: {response_data.get('error')}")
                return False
        else:
            print(f"❌ POST request failed with status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chat_get_request():
    """Test that chat GET request works correctly"""
    
    print("\n=== Testing Chat GET Request ===\n")
    
    try:
        # Get a test client
        client = CustomUser.objects.filter(role='client').first()
        if not client:
            print("❌ No client users found in database")
            return False
        
        # Test GET request
        factory = RequestFactory()
        request = factory.get('/chat/')
        request.user = client
        
        print("=== Testing GET request ===")
        
        # Call the chat_view function with GET request
        response = chat_view(request)
        
        # Check if the response is successful
        if response.status_code == 200:
            print("✅ GET request successful")
            return True
        else:
            print(f"❌ GET request failed with status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test1_result = test_chat_message_sending()
    test2_result = test_chat_get_request()
    
    print(f"\n=== Test Results ===")
    print(f"Chat message sending test: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    print(f"Chat GET request test: {'✅ PASSED' if test2_result else '❌ FAILED'}")
    
    if test1_result and test2_result:
        print("\n🎉 All tests passed! The chat message sending should work correctly.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")