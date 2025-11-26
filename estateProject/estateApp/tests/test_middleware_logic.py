#!/usr/bin/env python
"""
Test session timeout middleware logic
"""
import time
from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser
from estateApp.middleware import SessionExpirationMiddleware, TenantIsolationMiddleware


class MiddlewareLogicTestCase(TestCase):
    """Test middleware security logic"""

    def setUp(self):
        self.factory = RequestFactory()
        self.session_middleware = SessionMiddleware(lambda r: None)
        self.expiration_middleware = SessionExpirationMiddleware(lambda r: None)
        self.isolation_middleware = TenantIsolationMiddleware(lambda r: None)

    def test_session_expiration_fresh_session(self):
        """Test fresh session gets expiry set"""
        request = self.factory.get('/dashboard/')
        self.session_middleware.process_request(request)

        # Mock authenticated user
        request.user = type('MockUser', (), {
            'is_anonymous': False,
            'email': 'test@example.com'
        })()

        result = self.expiration_middleware.process_request(request)

        # Should not redirect (None return)
        self.assertIsNone(result)
        # Should have set session expiry
        self.assertIn('_session_expiry', request.session)

    def test_session_expiration_expired_session(self):
        """Test expired session redirects to login"""
        request = self.factory.get('/dashboard/')
        self.session_middleware.process_request(request)

        # Mock authenticated user
        request.user = type('MockUser', (), {
            'is_anonymous': False,
            'email': 'test@example.com'
        })()

        # Set expired session
        request.session['_session_expiry'] = time.time() - 100  # Expired
        request.session.save()

        result = self.expiration_middleware.process_request(request)

        # Should redirect to login
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 302)
        self.assertIn('/login/', result['Location'])

    def test_session_expiration_valid_session_renewal(self):
        """Test valid session gets renewed on activity"""
        request = self.factory.get('/dashboard/')
        self.session_middleware.process_request(request)

        # Mock authenticated user
        request.user = type('MockUser', (), {
            'is_anonymous': False,
            'email': 'test@example.com'
        })()

        # Set valid session
        old_expiry = time.time() + 100
        request.session['_session_expiry'] = old_expiry
        request.session.save()

        result = self.expiration_middleware.process_request(request)

        # Should not redirect
        self.assertIsNone(result)
        # Should have renewed expiry
        new_expiry = request.session['_session_expiry']
        self.assertGreater(new_expiry, old_expiry)

    def test_tenant_isolation_anonymous_user(self):
        """Test anonymous users get no company context"""
        request = self.factory.get('/dashboard/')
        request.user = AnonymousUser()

        result = self.isolation_middleware.process_request(request)

        # Should not redirect
        self.assertIsNone(result)
        # Should have no company context
        from estateApp.middleware import get_current_company
        self.assertIsNone(get_current_company())

    def test_tenant_isolation_public_endpoint(self):
        """Test public endpoints skip tenant isolation"""
        request = self.factory.get('/login/')
        request.user = AnonymousUser()

        result = self.isolation_middleware.process_request(request)

        # Should not redirect
        self.assertIsNone(result)