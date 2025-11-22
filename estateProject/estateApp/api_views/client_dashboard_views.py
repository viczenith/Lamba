"""
API Views for Client Dashboard and Cross-Company Property Management
Allows clients to view and manage properties from multiple companies
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models

from estateApp.models import (
    ClientDashboard, ClientPropertyView, EstatePlot,
    PlotAllocation, CustomUser
)
from estateApp.serializers.company_serializers import (
    ClientDashboardSerializer, ClientPropertyViewSerializer
)


class ClientDashboardViewSet(viewsets.ModelViewSet):
    """
    Client Portfolio Dashboard
    Allows clients to view aggregated properties across all companies
    """
    serializer_class = ClientDashboardSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Only clients can see their own dashboard"""
        if self.request.user.role == 'client':
            return ClientDashboard.objects.filter(client=self.request.user)
        return ClientDashboard.objects.none()
    
    @action(detail=False, methods=['get'])
    def my_dashboard(self, request):
        """Get current client's dashboard"""
        try:
            dashboard = ClientDashboard.objects.get(client=request.user)
            dashboard.refresh_portfolio_data()  # Refresh metrics
            serializer = self.get_serializer(dashboard)
            return Response(serializer.data)
        except ClientDashboard.DoesNotExist:
            # Create dashboard if it doesn't exist
            dashboard = ClientDashboard.objects.create(client=request.user)
            dashboard.refresh_portfolio_data()
            serializer = self.get_serializer(dashboard)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def my_properties(self, request):
        """Get all properties owned by the client across all companies"""
        allocations = PlotAllocation.objects.filter(
            client=request.user
        ).select_related(
            'plot__estate__company'
        ).order_by('-date_allocated')
        
        properties = []
        for allocation in allocations:
            properties.append({
                'id': allocation.id,
                'plot_id': allocation.plot.id,
                'estate': allocation.plot.estate.name,
                'plot_number': allocation.plot.plot_number,
                'company': allocation.plot.estate.company.company_name,
                'company_id': allocation.plot.estate.company.id,
                'amount_paid': str(allocation.amount_paid),
                'status': allocation.status,
                'date_allocated': allocation.date_allocated,
                'location': allocation.plot.estate.location,
            })
        
        return Response({
            'total_properties': len(properties),
            'properties': properties
        })
    
    @action(detail=False, methods=['get'])
    def portfolio_summary(self, request):
        """Get summarized portfolio stats"""
        allocations = PlotAllocation.objects.filter(client=request.user)
        
        total_invested = allocations.aggregate(
            total=models.Sum('amount_paid')
        )['total'] or 0
        
        companies = allocations.values(
            'plot__estate__company__company_name'
        ).distinct().count()
        
        return Response({
            'total_properties': allocations.count(),
            'total_invested': str(total_invested),
            'companies': companies,
            'portfolio_status': 'active' if allocations.exists() else 'empty'
        })


class ClientPropertyViewViewSet(viewsets.ModelViewSet):
    """
    Track client interest in properties across companies
    Allows clients to:
    - View all available properties from all companies
    - Mark properties as interested/favorited
    - Add notes to properties
    """
    serializer_class = ClientPropertyViewSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['plot__estate__name', 'plot__plot_number']
    ordering_fields = ['last_viewed_at', 'view_count']
    ordering = ['-last_viewed_at']
    
    def get_queryset(self):
        """Clients can only see their own viewed properties"""
        if self.request.user.role == 'client':
            return ClientPropertyView.objects.filter(client=self.request.user)
        return ClientPropertyView.objects.none()
    
    @action(detail=False, methods=['get'])
    def all_available_properties(self, request):
        """
        Get all available properties from all companies
        Clients can search across the entire platform
        """
        # Get all available plots from all companies
        available_plots = EstatePlot.objects.filter(
            status='available'
        ).select_related(
            'estate__company', 'plot_size'
        ).order_by('-created_at')
        
        # Apply filters if provided
        estate_filter = request.query_params.get('estate')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        location = request.query_params.get('location')
        
        if estate_filter:
            available_plots = available_plots.filter(estate__name__icontains=estate_filter)
        
        if min_price:
            available_plots = available_plots.filter(price__gte=float(min_price))
        
        if max_price:
            available_plots = available_plots.filter(price__lte=float(max_price))
        
        if location:
            available_plots = available_plots.filter(estate__location__icontains=location)
        
        # Format response
        properties = []
        for plot in available_plots[:50]:  # Limit to 50 results
            # Check if client has viewed this property
            view = ClientPropertyView.objects.filter(
                client=request.user,
                plot=plot
            ).first()
            
            properties.append({
                'id': plot.id,
                'plot_number': plot.plot_number,
                'estate': plot.estate.name,
                'company': plot.estate.company.company_name,
                'company_id': plot.estate.company.id,
                'price': str(plot.price),
                'location': plot.estate.location,
                'plot_size': plot.plot_size.size_sqm if plot.plot_size else None,
                'status': plot.status,
                'viewed_at': view.last_viewed_at if view else None,
                'view_count': view.view_count if view else 0,
                'is_interested': view.is_interested if view else False,
                'is_favorited': view.is_favorited if view else False,
            })
        
        return Response({
            'total_available': available_plots.count(),
            'shown': len(properties),
            'properties': properties
        })
    
    @action(detail=False, methods=['get'])
    def my_favorites(self, request):
        """Get all properties marked as favorites by client"""
        favorites = self.get_queryset().filter(is_favorited=True)
        serializer = self.get_serializer(favorites, many=True)
        return Response({
            'total_favorites': favorites.count(),
            'favorites': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def my_interested(self, request):
        """Get all properties client is interested in"""
        interested = self.get_queryset().filter(is_interested=True)
        serializer = self.get_serializer(interested, many=True)
        return Response({
            'total_interested': interested.count(),
            'interested_properties': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def track_view(self, request):
        """
        Track a property view for analytics
        Called when client views a property
        """
        plot_id = request.data.get('plot_id')
        
        try:
            plot = EstatePlot.objects.get(id=plot_id)
        except EstatePlot.DoesNotExist:
            return Response(
                {'error': 'Property not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create or update view
        view, created = ClientPropertyView.objects.get_or_create(
            client=request.user,
            plot=plot
        )
        
        if not created:
            view.view_count += 1
            view.save()
        
        serializer = self.get_serializer(view)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def toggle_favorite(self, request):
        """Toggle favorite status for a property"""
        plot_id = request.data.get('plot_id')
        
        try:
            plot = EstatePlot.objects.get(id=plot_id)
        except EstatePlot.DoesNotExist:
            return Response(
                {'error': 'Property not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        view, _ = ClientPropertyView.objects.get_or_create(
            client=request.user,
            plot=plot
        )
        
        view.is_favorited = not view.is_favorited
        view.save()
        
        return Response({
            'plot_id': plot_id,
            'is_favorited': view.is_favorited
        })
    
    @action(detail=False, methods=['post'])
    def toggle_interested(self, request):
        """Toggle interested status for a property"""
        plot_id = request.data.get('plot_id')
        
        try:
            plot = EstatePlot.objects.get(id=plot_id)
        except EstatePlot.DoesNotExist:
            return Response(
                {'error': 'Property not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        view, _ = ClientPropertyView.objects.get_or_create(
            client=request.user,
            plot=plot
        )
        
        view.is_interested = not view.is_interested
        view.save()
        
        return Response({
            'plot_id': plot_id,
            'is_interested': view.is_interested
        })
    
    @action(detail=False, methods=['post'])
    def add_note(self, request):
        """Add or update notes on a property"""
        plot_id = request.data.get('plot_id')
        notes = request.data.get('notes', '')
        
        try:
            plot = EstatePlot.objects.get(id=plot_id)
        except EstatePlot.DoesNotExist:
            return Response(
                {'error': 'Property not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        view, _ = ClientPropertyView.objects.get_or_create(
            client=request.user,
            plot=plot
        )
        
        view.client_notes = notes
        view.save()
        
        return Response({
            'plot_id': plot_id,
            'notes': view.client_notes,
            'updated_at': view.last_viewed_at
        })
