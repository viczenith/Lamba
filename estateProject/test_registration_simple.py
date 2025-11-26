import os
import django
from django.conf import settings
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.views import client_registration, marketer_registration
from estateApp.models import CustomUser

def get_response(request):
    return None

def test_registration():
    factory = RequestFactory()

    # Test client registration
    print("Testing client registration...")
    request = factory.post('/client/register/', {
        'first_name': 'Test',
        'last_name': 'Client',
        'email': 'testclient@example.com',
        'phone': '+1234567890',
        'date_of_birth': '1990-01-01',
        'password': 'testpassword123',
        'confirm_password': 'testpassword123'
    })

    # Add middleware manually
    middleware = SessionMiddleware(get_response)
    middleware.process_request(request)
    request.session.save()

    middleware = MessageMiddleware(get_response)
    middleware.process_request(request)
    request.session.save()

    try:
        response = client_registration(request)
        print(f"Client registration response status: {response.status_code}")
        if hasattr(response, 'content'):
            print(f"Response content: {response.content.decode()[:500]}")
    except Exception as e:
        print(f"Client registration error: {e}")
        import traceback
        traceback.print_exc()

    # Test marketer registration
    print("\nTesting marketer registration...")
    request = factory.post('/marketer/register/', {
        'first_name': 'Test',
        'last_name': 'Marketer',
        'email': 'testmarketer@example.com',
        'phone': '+1234567890',
        'date_of_birth': '1990-01-01',
        'password': 'testpassword123',
        'confirm_password': 'testpassword123'
    })

    # Add middleware manually
    middleware = SessionMiddleware(get_response)
    middleware.process_request(request)
    request.session.save()

    middleware = MessageMiddleware(get_response)
    middleware.process_request(request)
    request.session.save()

    try:
        response = marketer_registration(request)
        print(f"Marketer registration response status: {response.status_code}")
        if hasattr(response, 'content'):
            print(f"Response content: {response.content.decode()[:500]}")
    except Exception as e:
        print(f"Marketer registration error: {e}")
        import traceback
        traceback.print_exc()

    # Check if users were created
    print("\nChecking created users...")
    try:
        client = CustomUser.objects.get(email='testclient@example.com')
        print(f"Client created: ID={client.id}, Email={client.email}, DOB={client.date_of_birth}")
    except CustomUser.DoesNotExist:
        print("Client was not created")

    try:
        marketer = CustomUser.objects.get(email='testmarketer@example.com')
        print(f"Marketer created: ID={marketer.id}, Email={marketer.email}, DOB={marketer.date_of_birth}")
    except CustomUser.DoesNotExist:
        print("Marketer was not created")

if __name__ == '__main__':
    test_registration()