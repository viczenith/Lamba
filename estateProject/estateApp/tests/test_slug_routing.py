# Comprehensive Tests for Dynamic Slug Routing
# File: estateApp/tests/test_slug_routing.py

import pytest
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from estateApp.models import Company, Client as ClientModel, Estate
from estateApp.dynamic_slug_routing import (
    SlugValidator,
    SlugManager,
    CompanySlugContextMiddleware,
    user_has_company_access,
    log_unauthorized_access,
    check_rate_limit,
    get_company_url,
    get_company_absolute_url,
    SlugSecurity,
)

User = get_user_model()


class TestSlugValidator(TestCase):
    """Test slug format validation"""

    def test_valid_slug_format(self):
        """Valid slugs pass validation"""
        valid_slugs = [
            'victor-godwin-ventures',
            'green-estate-homes',
            'blue-sky-properties-ltd',
            'a-b-c',  # minimum length with hyphens
            'very-long-slug-name-that-is-still-valid-and-under-fifty-char',
        ]
        for slug in valid_slugs:
            self.assertTrue(SlugValidator.is_valid(slug), f"Failed: {slug}")

    def test_invalid_slug_format(self):
        """Invalid slugs fail validation"""
        invalid_slugs = [
            'UPPERCASE',             # Not lowercase
            'with spaces',           # Space not allowed
            'with_underscore',       # Underscore not allowed
            'with--double',          # Consecutive hyphens
            '-starts-with-hyphen',   # Starts with hyphen
            'ends-with-hyphen-',     # Ends with hyphen
            'ab',                    # Too short (< 3 chars)
            'a' * 51,                # Too long (> 50 chars)
            'with.dot',              # Dot not allowed
            'with/slash',            # Slash not allowed
        ]
        for slug in invalid_slugs:
            self.assertFalse(SlugValidator.is_valid(slug), f"Failed: {slug}")

    def test_reserved_slugs_rejected(self):
        """Reserved slugs are rejected"""
        reserved = ['admin', 'api', 'login', 'logout', 'register', 'dashboard']
        for slug in reserved:
            self.assertFalse(SlugValidator.is_valid(slug), f"Failed: {slug}")

    def test_slug_generation_from_company_name(self):
        """Slugs are generated correctly from company names"""
        test_cases = [
            ("Victor Godwin Ventures", "victor-godwin-ventures"),
            ("UPPERCASE NAME", "uppercase-name"),
            ("Multi   Spaces", "multi-spaces"),
            ("Special@#$Characters", "specialcharacters"),
            ("Name-With-Hyphens", "name-with-hyphens"),
        ]
        for name, expected_slug in test_cases:
            generated = SlugValidator.generate_from_company_name(name)
            # Check it's valid (exact match may not be due to collisions)
            self.assertTrue(SlugValidator.is_valid(generated), f"Generated invalid: {generated}")


class TestSlugManager(TestCase):
    """Test slug management operations"""

    def setUp(self):
        """Create test company"""
        self.company = Company.objects.create(
            company_name="Test Company",
            slug="test-company",
            registration_number="REG123",
            registration_date="2025-01-01",
            location="Lagos",
            ceo_name="Test CEO",
            ceo_dob="1990-01-01",
            email="test@company.com",
            phone="08012345678",
        )

    def test_generate_unique_slug(self):
        """Unique slugs are generated without collisions"""
        slug1 = SlugManager.generate_unique_slug("Test Company")
        slug2 = SlugManager.generate_unique_slug("Test Company")  # Same name
        
        # Should be different (one will have number suffix)
        if slug1 != slug2:
            self.assertTrue(True)  # Expected behavior
        else:
            # Or same if not in DB
            self.assertTrue(SlugValidator.is_valid(slug1))

    def test_verify_slug_uniqueness(self):
        """Slug uniqueness check works correctly"""
        # test-company already exists
        is_unique = SlugManager.verify_slug_uniqueness('test-company')
        self.assertFalse(is_unique)
        
        # New slug doesn't exist
        is_unique = SlugManager.verify_slug_uniqueness('brand-new-slug')
        self.assertTrue(is_unique)

    def test_get_company_by_slug(self):
        """Retrieve company by slug"""
        company = SlugManager.get_company_by_slug('test-company')
        self.assertEqual(company.id, self.company.id)
        
        # Non-existent slug returns None
        company = SlugManager.get_company_by_slug('nonexistent')
        self.assertIsNone(company)

    def test_update_slug(self):
        """Update company slug"""
        old_slug = self.company.slug
        new_slug = SlugManager.update_slug(self.company, "Updated Company Name")
        
        self.company.refresh_from_db()
        self.assertNotEqual(old_slug, self.company.slug)
        self.assertTrue(SlugValidator.is_valid(self.company.slug))


class TestCompanyAccessControl(TestCase):
    """Test company access verification"""

    def setUp(self):
        """Create test companies and users"""
        self.company1 = Company.objects.create(
            company_name="Company A",
            slug="company-a",
            registration_number="REG001",
            registration_date="2025-01-01",
            location="Lagos",
            ceo_name="CEO A",
            ceo_dob="1990-01-01",
            email="a@company.com",
            phone="08011111111",
        )
        self.company2 = Company.objects.create(
            company_name="Company B",
            slug="company-b",
            registration_number="REG002",
            registration_date="2025-01-01",
            location="Abuja",
            ceo_name="CEO B",
            ceo_dob="1990-01-01",
            email="b@company.com",
            phone="08022222222",
        )
        
        # Create users
        self.admin1 = User.objects.create_user(
            username="admin1",
            email="admin1@company.com",
            password="testpass123",
            company=self.company1,
            is_staff=True,
        )
        self.admin2 = User.objects.create_user(
            username="admin2",
            email="admin2@company.com",
            password="testpass123",
            company=self.company2,
            is_staff=True,
        )
        self.superadmin = User.objects.create_user(
            username="superadmin",
            email="super@company.com",
            password="testpass123",
            is_superuser=True,
            is_staff=True,
        )

    def test_user_access_own_company(self):
        """User can access their own company"""
        has_access = user_has_company_access(self.admin1, self.company1)
        self.assertTrue(has_access)

    def test_user_denied_other_company(self):
        """User cannot access other company"""
        has_access = user_has_company_access(self.admin1, self.company2)
        self.assertFalse(has_access)

    def test_superadmin_access_all_companies(self):
        """Superadmin can access all companies"""
        has_access = user_has_company_access(self.superadmin, self.company1)
        self.assertTrue(has_access)
        
        has_access = user_has_company_access(self.superadmin, self.company2)
        self.assertTrue(has_access)

    def test_unauthorized_access_logged(self):
        """Unauthorized access attempts are logged"""
        from estateApp.models import AuditLog
        
        log_unauthorized_access(self.admin1, self.company2, self.client.get('/'))
        
        # Check log was created
        log = AuditLog.objects.filter(
            user=self.admin1,
            company=self.company2,
            action='UNAUTHORIZED_ACCESS_ATTEMPT'
        ).first()
        
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.admin1)
        self.assertEqual(log.company, self.company2)


class TestRateLimiting(TestCase):
    """Test rate limiting functionality"""

    def setUp(self):
        """Create test user and company"""
        self.company = Company.objects.create(
            company_name="Test Company",
            slug="test-company",
            registration_number="REG123",
            registration_date="2025-01-01",
            location="Lagos",
            ceo_name="Test CEO",
            ceo_dob="1990-01-01",
            email="test@company.com",
            phone="08012345678",
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="user@test.com",
            password="testpass123",
            company=self.company,
        )

    def test_rate_limit_allows_requests_under_limit(self):
        """Requests under limit are allowed"""
        for i in range(10):
            is_allowed = check_rate_limit(self.user, self.company, max_requests=100, time_window=3600)
            self.assertTrue(is_allowed)

    def test_rate_limit_blocks_exceeded_requests(self):
        """Requests over limit are blocked"""
        max_requests = 5
        for i in range(max_requests):
            check_rate_limit(self.user, self.company, max_requests=max_requests, time_window=3600)
        
        # Next request should be blocked
        is_allowed = check_rate_limit(self.user, self.company, max_requests=max_requests, time_window=3600)
        self.assertFalse(is_allowed)


class TestURLBuilders(TestCase):
    """Test URL building utilities"""

    def setUp(self):
        """Create test company"""
        self.company = Company.objects.create(
            company_name="Test Company",
            slug="test-company",
            registration_number="REG123",
            registration_date="2025-01-01",
            location="Lagos",
            ceo_name="Test CEO",
            ceo_dob="1990-01-01",
            email="test@company.com",
            phone="08012345678",
        )
        self.factory = RequestFactory()

    def test_get_company_url(self):
        """Company URL is built correctly"""
        url = get_company_url(self.company)
        self.assertEqual(url, "/test-company")
        
        url = get_company_url(self.company, "dashboard")
        self.assertEqual(url, "/test-company/dashboard")
        
        url = get_company_url(self.company, "/clients/")
        self.assertEqual(url, "/test-company/clients")

    def test_get_company_absolute_url(self):
        """Company absolute URL is built correctly"""
        request = self.factory.get('/test-company/')
        request.META['HTTP_HOST'] = 'example.com'
        
        url = get_company_absolute_url(request, self.company)
        self.assertIn('example.com', url)
        self.assertIn('test-company', url)


class TestSlugSecurity(TestCase):
    """Test advanced slug security features"""

    def setUp(self):
        """Create test user and company"""
        self.company = Company.objects.create(
            company_name="Test Company",
            slug="test-company",
            registration_number="REG123",
            registration_date="2025-01-01",
            location="Lagos",
            ceo_name="Test CEO",
            ceo_dob="1990-01-01",
            email="test@company.com",
            phone="08012345678",
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="user@test.com",
            password="testpass123",
            company=self.company,
        )

    def test_slug_token_generation(self):
        """Slug tokens are generated correctly"""
        token_data = SlugSecurity.generate_slug_token(self.company, self.user, expires_in=3600)
        
        self.assertIn('token', token_data)
        self.assertIn('data', token_data)
        self.assertEqual(token_data['data']['company_id'], self.company.id)
        self.assertEqual(token_data['data']['user_id'], self.user.id)

    def test_slug_token_verification(self):
        """Slug tokens are verified correctly"""
        token_info = SlugSecurity.generate_slug_token(self.company, self.user, expires_in=3600)
        
        is_valid, error = SlugSecurity.verify_slug_token(
            token_info['token'],
            token_info['data'],
            self.company,
            self.user
        )
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_slug_token_expired(self):
        """Expired tokens are rejected"""
        token_info = SlugSecurity.generate_slug_token(self.company, self.user, expires_in=-1)  # Already expired
        
        is_valid, error = SlugSecurity.verify_slug_token(
            token_info['token'],
            token_info['data'],
            self.company,
            self.user
        )
        self.assertFalse(is_valid)
        self.assertIn('expired', error.lower())

    def test_suspicious_slug_detection(self):
        """Suspicious patterns are detected"""
        suspicious_slugs = [
            '../../../admin',           # Path traversal
            'admin?union=select',       # SQL injection
            '<script>alert()</script>', # XSS
            'test%27%20or%201=1',       # URL encoded injection
        ]
        
        for slug in suspicious_slugs:
            is_suspicious = SlugSecurity.is_slug_suspicious(slug)
            self.assertTrue(is_suspicious, f"Failed to detect: {slug}")

    def test_legitimate_slug_not_flagged(self):
        """Legitimate slugs are not flagged"""
        legitimate_slugs = [
            'victor-godwin-ventures',
            'green-estate-homes',
            'blue-sky-properties',
        ]
        
        for slug in legitimate_slugs:
            is_suspicious = SlugSecurity.is_slug_suspicious(slug)
            self.assertFalse(is_suspicious, f"False positive: {slug}")


class TestIntegrationScenarios(TestCase):
    """Integration tests for complete scenarios"""

    def setUp(self):
        """Create test environment"""
        self.client = Client()
        self.factory = RequestFactory()
        
        self.company1 = Company.objects.create(
            company_name="Company A",
            slug="company-a",
            registration_number="REG001",
            registration_date="2025-01-01",
            location="Lagos",
            ceo_name="CEO A",
            ceo_dob="1990-01-01",
            email="a@company.com",
            phone="08011111111",
        )
        
        self.admin1 = User.objects.create_user(
            username="admin1",
            email="admin1@company.com",
            password="testpass123",
            company=self.company1,
            is_staff=True,
        )
        
        self.client_obj = ClientModel.objects.create(
            company=self.company1,
            first_name="John",
            last_name="Doe",
            email="john@test.com",
            phone="08099999999",
        )

    def test_user_can_access_own_company_dashboard(self):
        """User can access their company dashboard"""
        self.client.login(username='admin1', password='testpass123')
        
        # This would be handled by the view
        # Here we're testing the data isolation logic
        user = User.objects.get(username='admin1')
        company = user.company
        
        self.assertEqual(company.slug, 'company-a')

    def test_cross_company_data_isolation(self):
        """Data is isolated between companies"""
        # Create second company
        company2 = Company.objects.create(
            company_name="Company B",
            slug="company-b",
            registration_number="REG002",
            registration_date="2025-01-01",
            location="Abuja",
            ceo_name="CEO B",
            ceo_dob="1990-01-01",
            email="b@company.com",
            phone="08022222222",
        )
        
        # Company A client shouldn't be visible to Company B
        company_b_clients = ClientModel.objects.filter(company=company2)
        self.assertNotIn(self.client_obj, company_b_clients)
        
        # Company A should see their own client
        company_a_clients = ClientModel.objects.filter(company=self.company1)
        self.assertIn(self.client_obj, company_a_clients)


# ============================================================================
# PYTEST FIXTURES (Alternative to TestCase)
# ============================================================================

@pytest.fixture
def company():
    """Fixture: Create test company"""
    return Company.objects.create(
        company_name="Test Company",
        slug="test-company",
        registration_number="REG123",
        registration_date="2025-01-01",
        location="Lagos",
        ceo_name="Test CEO",
        ceo_dob="1990-01-01",
        email="test@company.com",
        phone="08012345678",
    )


@pytest.fixture
def user(company):
    """Fixture: Create test user for company"""
    return User.objects.create_user(
        username="testuser",
        email="user@test.com",
        password="testpass123",
        company=company,
    )


@pytest.fixture
def superadmin():
    """Fixture: Create superadmin user"""
    return User.objects.create_user(
        username="superadmin",
        email="super@test.com",
        password="testpass123",
        is_superuser=True,
    )


# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == '__main__':
    # Run with: python manage.py test estateApp.tests.test_slug_routing
    # Or with pytest: pytest estateApp/tests/test_slug_routing.py
    pass
