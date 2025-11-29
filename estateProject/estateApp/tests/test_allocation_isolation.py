from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone

from estateApp import views
from estateApp.models import (
    Company, Estate, PlotNumber, PlotSize, EstatePlot, PlotSizeUnits,
    PlotAllocation, ClientUser
)

User = get_user_model()


class AllocationIsolationTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        # Create two companies (provide required fields)
        today = timezone.now().date()
        self.company_a = Company.objects.create(
            company_name='Company A',
            slug='comp-a',
            registration_number='R-A',
            registration_date=today,
            location='Loc A',
            ceo_name='CEO A',
            ceo_dob=today,
            email='compa@example.com',
            phone='100'
        )
        self.company_b = Company.objects.create(
            company_name='Company B',
            slug='comp-b',
            registration_number='R-B',
            registration_date=today,
            location='Loc B',
            ceo_name='CEO B',
            ceo_dob=today,
            email='compb@example.com',
            phone='200'
        )

        # Create admin users for each company using manager helper
        self.user_a = User.objects.create_user(email='a@example.com', full_name='User A', phone='111', password='pass')
        self.user_a.company_profile = self.company_a
        self.user_a.save()

        self.user_b = User.objects.create_user(email='b@example.com', full_name='User B', phone='222', password='pass')
        self.user_b.company_profile = self.company_b
        self.user_b.save()

        # Create estates for each company
        self.estate_a = Estate.objects.create(
            company=self.company_a,
            name='Estate A',
            location='LocA',
            estate_size='10 acres',
            title_deed='RofO'
        )
        self.estate_b = Estate.objects.create(
            company=self.company_b,
            name='Estate B',
            location='LocB',
            estate_size='5 acres',
            title_deed='RofO'
        )

        # Create plot numbers for each company and link to estate plots
        self.plot_number_a = PlotNumber.objects.create(number='A1', company=self.company_a)
        self.plot_number_b = PlotNumber.objects.create(number='B1', company=self.company_b)

        self.estate_plot_a = EstatePlot.objects.create(estate=self.estate_a)
        self.estate_plot_b = EstatePlot.objects.create(estate=self.estate_b)

        self.estate_plot_a.plot_numbers.add(self.plot_number_a)
        self.estate_plot_b.plot_numbers.add(self.plot_number_b)

        # Create plot sizes and units
        self.plot_size = PlotSize.objects.create(size='100', company=self.company_a)
        self.plot_unit_a = PlotSizeUnits.objects.create(estate_plot=self.estate_plot_a, plot_size=self.plot_size, total_units=1, available_units=1)

        # Create a client for company A
        self.client_a = ClientUser.objects.create_user(email='clienta@example.com', full_name='Client A', phone='333', password='pass')
        self.client_a.company_profile = self.company_a
        self.client_a.save()

        # Create an allocation for company A
        self.allocation_a = PlotAllocation.objects.create(
            plot_size_unit=self.plot_unit_a,
            client=self.client_a,
            estate=self.estate_a,
            plot_size=self.plot_size,
            payment_type='part'
        )

    def test_get_allocated_plots_scoped_to_company(self):
        request = self.factory.get('/dummy')
        request.user = self.user_a

        response = views.get_allocated_plots(request)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should contain only allocations for company A
        self.assertIsInstance(data, list)
        self.assertTrue(any(item.get('estate_id') == self.estate_a.id for item in data))
        self.assertFalse(any(item.get('estate_id') == self.estate_b.id for item in data))

    def test_available_plot_numbers_scoped(self):
        request = self.factory.get('/dummy')
        request.user = self.user_a

        response = views.available_plot_numbers(request, self.estate_a.id)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should return plot numbers for company A and estate A
        ids = [p['id'] for p in data]
        self.assertIn(self.plot_number_a.id, ids)
        self.assertNotIn(self.plot_number_b.id, ids)