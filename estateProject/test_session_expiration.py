#!/usr/bin/env python
"""
Test script to verify session expiration redirects work correctly.
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from estateApp.middleware import SessionExpirationMiddleware

def test_session_expiration():
    """Test session expiration middleware"""
    print("Testing session expiration middleware...")

    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/accounts/profile/')

    # Add session middleware
    middleware = SessionMiddleware()
    middleware.process_request(request)
    request.session.save()

    # Simulate expired session
    expired_time = (datetime.now() - timedelta(minutes=10)).timestamp()
    request.session['_session_expiry'] = expired_time

    # Create session expiration middleware
    session_middleware = SessionExpirationMiddleware()

    # Process the request
    response = session_middleware.process_request(request)

    if response:
        print(f"✅ Session expiration redirect triggered: {response.status_code}")
        print(f"Redirect location: {response.get('Location', 'None')}")
    else:
        print("❌ Session expiration not triggered")

    # Test with valid session
    valid_time = (datetime.now() + timedelta(minutes=10)).timestamp()
    request.session['_session_expiry'] = valid_time

    response = session_middleware.process_request(request)
    if response is None:
        print("✅ Valid session allowed to proceed")
    else:
        print("❌ Valid session was blocked")

if __name__ == '__main__':
    test_session_expiration()