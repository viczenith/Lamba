import unittest
from unittest.mock import patch, MagicMock

from django.test import RequestFactory

from estateApp.forms import CustomAuthenticationForm
from estateApp.backends import EmailBackend, MultipleUserMatch


class AuthFormTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch('estateApp.forms.authenticate')
    @patch('estateApp.forms.Company')
    def test_form_passes_company_when_slug_present(self, mock_company_model, mock_authenticate):
        # Arrange: create a request with resolver_match.kwargs containing login_slug
        request = self.factory.post('/dummy', data={'username': 'x@example.com', 'password': 'p'})
        request.resolver_match = MagicMock(kwargs={'login_slug': 'comp-x'})

        fake_company = MagicMock()
        mock_company_model.objects.get.return_value = fake_company

        form = CustomAuthenticationForm(data={'username': 'x@example.com', 'password': 'p'})
        # Attach request to form as Django does when instantiating via view
        form.request = request

        # Act: call is_valid() to populate cleaned_data and invoke clean()
        form.is_valid()

        # Assert: authenticate called with company arg
        mock_authenticate.assert_called()
        # Verify at least one call contained a 'company' kwarg
        called_with_company = any(('company' in call.kwargs) for call in mock_authenticate.call_args_list)
        self.assertTrue(called_with_company)

    @patch('estateApp.forms.authenticate')
    def test_form_does_not_pass_company_when_no_slug(self, mock_authenticate):
        request = self.factory.post('/dummy', data={'username': 'x@example.com', 'password': 'p'})
        request.resolver_match = MagicMock(kwargs={})

        form = CustomAuthenticationForm(data={'username': 'x@example.com', 'password': 'p'})
        form.request = request

        form.is_valid()

        mock_authenticate.assert_called()
        called_with_company = any(('company' in call.kwargs) for call in mock_authenticate.call_args_list)
        self.assertFalse(called_with_company)


class EmailBackendUnitTests(unittest.TestCase):
    def test_multiple_user_match_returned_when_multiple_users_have_password(self):
        # Create fake users where two have check_password True
        class FakeUser:
            def __init__(self, email, pw_ok, role='client'):
                self.email = email
                self._pw_ok = pw_ok
                self.role = role

            def check_password(self, pw):
                return self._pw_ok

        users = [FakeUser('a@example.com', True, role='client'), FakeUser('a@example.com', True, role='marketer')]

        # Patch CustomUser.objects.filter to return our fake users
        # Patch the CustomUser reference imported into the backend module so
        # its `objects.filter` returns our fake users.
        fake_model = MagicMock()
        fake_manager = MagicMock()
        fake_manager.filter.return_value = users
        fake_model.objects = fake_manager

        with patch('estateApp.backends.CustomUser', fake_model):
            backend = EmailBackend()
            result = backend.authenticate(request=None, username='a@example.com', password='pw')

            self.assertIsNotNone(result)
            self.assertIsInstance(result, MultipleUserMatch)
            self.assertEqual(len(result.users), 2)


if __name__ == '__main__':
    unittest.main()
