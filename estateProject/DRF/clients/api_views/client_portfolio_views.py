"""
Client Cross-Company Portfolio Views
Allows clients to see all properties they've purchased across multiple companies
"""
from django.db.models import Sum, Count, Q, F
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from django.shortcuts import get_object_or_404
from decimal import Decimal

from estateApp.models import (
    CustomUser, PlotAllocation, Company, 
    ClientDashboard, Transaction, EstatePlot
)
from DRF.clients.serializers.permissions import IsClientUser


class ClientPortfolioOverviewAPIView(APIView):
    """
    GET /api/client/portfolio/overview/
    Returns aggregated portfolio data across all companies for the authenticated client
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsClientUser)

    def get(self, request):
        user = request.user
        
        # Ensure user is independent client (no company_profile)
        if hasattr(user, 'company_profile') and user.company_profile is not None:
            return Response({
                'error': 'This endpoint is for independent clients only. Company-assigned clients should use their company dashboard.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get or create client dashboard
        dashboard, created = ClientDashboard.objects.get_or_create(client=user)
        
        # Refresh portfolio data
        dashboard.refresh_portfolio_data()
        
        # Get all allocations by client email (cross-company tracking)
        allocations = PlotAllocation.objects.filter(
            client_email=user.email
        ).select_related(
            'estate__company', 'plot_size', 'estate', 'client'
        ).order_by('-date_allocated')
        
        # Group by company
        companies_data = {}
        for allocation in allocations:
            company = allocation.estate.company
            if not company:
                continue
                
            company_id = company.id
            if company_id not in companies_data:
                companies_data[company_id] = {
                    'company_id': company_id,
                    'company_name': company.company_name,
                    'company_logo': company.logo.url if company.logo else None,
                    'properties_count': 0,
                    'total_invested': Decimal('0.00'),
                    'properties': []
                }
            
            companies_data[company_id]['properties_count'] += 1
            companies_data[company_id]['total_invested'] += allocation.amount_paid or Decimal('0.00')
            companies_data[company_id]['properties'].append({
                'allocation_id': allocation.id,
                'estate_name': allocation.estate.estate_name,
                'estate_id': allocation.estate.id,
                'plot_number': allocation.plot_number.number if allocation.plot_number else 'N/A',
                'plot_size': str(allocation.plot_size),
                'amount_paid': str(allocation.amount_paid) if hasattr(allocation, 'amount_paid') else '0.00',
                'payment_type': allocation.payment_type,
                'allocation_date': allocation.date_allocated.isoformat() if allocation.date_allocated else None,
                'client_name': allocation.client.full_name if allocation.client else 'N/A',
                'status': getattr(allocation, 'status', 'Active'),
                'plot_image': allocation.estate.estate_image.url if allocation.estate.estate_image else None,
            })
        
        # Convert to list
        companies_list = list(companies_data.values())
        
        return Response({
            'overview': {
                'total_properties': dashboard.total_properties_owned,
                'total_invested': str(dashboard.total_invested),
                'portfolio_value': str(dashboard.portfolio_value),
                'roi_percentage': str(dashboard.roi_percentage),
                'companies_count': len(companies_list),
            },
            'companies': companies_list
        }, status=status.HTTP_200_OK)


class ClientCompaniesListAPIView(APIView):
    """
    GET /api/client/companies/
    Returns list of all companies the client has purchased properties from
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsClientUser)

    def get(self, request):
        user = request.user
        
        # Ensure user is independent client
        if hasattr(user, 'company_profile') and user.company_profile is not None:
            return Response({
                'error': 'This endpoint is for independent clients only.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get unique companies from client's allocations (by email)
        companies = Company.objects.filter(
            estates__plot_allocations__client_email=user.email
        ).distinct().annotate(
            properties_count=Count('estates__plot_allocations', filter=Q(estates__plot_allocations__client_email=user.email))
        ).values(
            'id', 'company_name', 'logo', 'email', 'phone', 
            'location', 'properties_count'
        )
        
        companies_list = []
        for company in companies:
            # Calculate total invested for this company
            total_invested = PlotAllocation.objects.filter(
                client_email=user.email,
                estate__company_id=company['id']
            ).aggregate(
                total=Sum('plot_size_unit__price')
            )['total'] or Decimal('0.00')
            
            companies_list.append({
                'id': company['id'],
                'name': company['company_name'],
                'logo': request.build_absolute_uri(company['logo']) if company['logo'] else None,
                'email': company['email'],
                'phone': company['phone'],
                'location': company['location'],
                'properties_count': company['properties_count'] or 0,
                'total_invested': str(total_invested)
            })
        
        return Response({
            'companies': companies_list,
            'total_companies': len(companies_list)
        }, status=status.HTTP_200_OK)


class ClientCompanyPropertiesAPIView(APIView):
    """
    GET /api/client/companies/<company_id>/properties/
    Returns all properties purchased by client from a specific company
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsClientUser)

    def get(self, request, company_id):
        user = request.user
        
        # Ensure user is independent client
        if hasattr(user, 'company_profile') and user.company_profile is not None:
            return Response({
                'error': 'This endpoint is for independent clients only.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Verify company exists
        company = get_object_or_404(Company, id=company_id)
        
        # Get allocations for this client from this company (by email)
        allocations = PlotAllocation.objects.filter(
            client_email=user.email,
            estate__company=company
        ).select_related(
            'estate', 'plot_size', 'plot_number', 'client'
        ).order_by('-date_allocated')
        
        properties_list = []
        total_invested = Decimal('0.00')
        
        for allocation in allocations:
            # Calculate investment for this allocation
            investment = getattr(allocation.plot_size_unit, 'price', Decimal('0.00')) if hasattr(allocation, 'plot_size_unit') else Decimal('0.00')
            total_invested += investment
            
            # Get transactions for this allocation (if Transaction model links to PlotAllocation)
            transactions_data = []
            if hasattr(allocation, 'transactions'):
                transactions = allocation.transactions.all().order_by('-transaction_date')
                for txn in transactions:
                    transactions_data.append({
                        'id': txn.id,
                        'transaction_date': txn.transaction_date.isoformat() if hasattr(txn, 'transaction_date') and txn.transaction_date else None,
                        'amount': str(txn.total_amount) if hasattr(txn, 'total_amount') else '0.00',
                        'payment_type': allocation.payment_type,
                        'status': 'Fully Paid' if allocation.payment_type == 'full' else 'Part Payment'
                    })
            
            properties_list.append({
                'allocation_id': allocation.id,
                'estate': {
                    'id': allocation.estate.id,
                    'name': allocation.estate.estate_name,
                    'location': allocation.estate.estate_location,
                    'image': request.build_absolute_uri(allocation.estate.estate_image.url) if allocation.estate.estate_image else None,
                },
                'plot_number': allocation.plot_number.number if allocation.plot_number else 'N/A',
                'plot_size': {
                    'size': str(allocation.plot_size.size),
                    'unit': allocation.plot_size.size_unit,
                },
                'amount_invested': str(investment),
                'payment_type': allocation.get_payment_type_display(),
                'allocation_date': allocation.date_allocated.isoformat() if allocation.date_allocated else None,
                'client_name': allocation.client.full_name if allocation.client else 'N/A',
                'status': getattr(allocation, 'status', 'Active'),
                'transactions': transactions_data,
                'transactions_count': len(transactions_data),
            })
        
        return Response({
            'company': {
                'id': company.id,
                'name': company.company_name,
                'logo': request.build_absolute_uri(company.logo.url) if company.logo else None,
                'email': company.email,
                'phone': company.phone,
                'location': company.location,
            },
            'properties': properties_list,
            'total_properties': len(properties_list),
            'total_invested': str(total_invested)
        }, status=status.HTTP_200_OK)


class ClientAllPropertiesAPIView(APIView):
    """
    GET /api/client/all-properties/
    Returns ALL properties client has purchased across all companies
    Includes company information with each property
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsClientUser)

    def get(self, request):
        user = request.user
        
        # Ensure user is independent client
        if hasattr(user, 'company_profile') and user.company_profile is not None:
            return Response({
                'error': 'This endpoint is for independent clients only.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get all allocations by email (cross-company)
        allocations = PlotAllocation.objects.filter(
            client_email=user.email
        ).select_related(
            'estate__company', 'estate', 'plot_size', 'plot_number', 'client'
        ).order_by('-date_allocated')
        
        properties_list = []
        total_invested = Decimal('0.00')
        
        for allocation in allocations:
            company = allocation.estate.company
            investment = getattr(allocation.plot_size_unit, 'price', Decimal('0.00')) if hasattr(allocation, 'plot_size_unit') else Decimal('0.00')
            total_invested += investment
            
            properties_list.append({
                'allocation_id': allocation.id,
                'company': {
                    'id': company.id if company else None,
                    'name': company.company_name if company else 'Unknown',
                    'logo': request.build_absolute_uri(company.logo.url) if (company and company.logo) else None,
                },
                'estate': {
                    'id': allocation.estate.id,
                    'name': allocation.estate.estate_name,
                    'location': allocation.estate.estate_location,
                    'image': request.build_absolute_uri(allocation.estate.estate_image.url) if allocation.estate.estate_image else None,
                },
                'plot_number': allocation.plot_number.number if allocation.plot_number else 'N/A',
                'plot_size': str(allocation.plot_size),
                'amount_invested': str(investment),
                'payment_type': allocation.get_payment_type_display(),
                'allocation_date': allocation.date_allocated.isoformat() if allocation.date_allocated else None,
                'client_name': allocation.client.full_name if allocation.client else 'N/A',
                'status': getattr(allocation, 'status', 'Active'),
            })
        
        return Response({
            'properties': properties_list,
            'total_properties': len(properties_list),
            'total_invested': str(total_invested)
        }, status=status.HTTP_200_OK)
