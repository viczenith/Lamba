from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class MarketerCompanyPortfolioAPITest(APITestCase):
    def test_portfolio_requires_authentication(self):
        """Unauthenticated requests should be rejected (401 or 403)."""
        url = reverse('drf:marketer-company-portfolio-page', kwargs={'company_id': 1})
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
