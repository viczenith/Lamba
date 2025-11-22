"""
Property Management ViewSets for DRF.
Migrates property, estate, and allocation endpoints to DRF.
"""
import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q, Count, Sum

from estateApp.models import (
    Estate, EstatePlot, PropertyPrice, PlotAllocation,
    PlotSize, PlotNumber
)
from ..serializers.estate_serializers import EstateSerializer
from ..serializers.estate_detail_serializers import EstatePlotDetailSerializer
from ..serializers.plot_allocation_serializer import PlotAllocationSerializer
from estateApp.permissions import (
    IsAuthenticated, SubscriptionRequiredPermission, TenantIsolationPermission,
    FeatureAccessPermission
)
from estateApp.throttles import SubscriptionTierThrottle
from estateApp.audit_logging import AuditLogger
from estateApp.error_tracking import track_errors, ErrorHandler
from estateApp.api_filters import (
    CompanyAwareFilterBackend, SearchFilterBackend, OrderingFilterBackend,
    DateRangeFilterBackend
)

logger = logging.getLogger(__name__)


class EstateViewSet(viewsets.ModelViewSet):
    """
    Estate management endpoints:
    - List estates
    - Create estate
    - Retrieve estate details
    - Update estate
    - Delete estate
    - Manage estate properties
    """
    
    permission_classes = [
        IsAuthenticated,
        SubscriptionRequiredPermission,
        TenantIsolationPermission,
    ]
    throttle_classes = [SubscriptionTierThrottle]
    serializer_class = EstateSerializer
    filter_backends = [
        CompanyAwareFilterBackend,
        SearchFilterBackend,
        OrderingFilterBackend,
        DateRangeFilterBackend,
    ]
    search_fields = ['name', 'location', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name', 'location']
    
    def get_queryset(self):
        """Get estates for user's company"""
        company = getattr(self.request, 'company', None)
        
        if company:
            return Estate.objects.filter(company=company)
        
        return Estate.objects.none()
    
    def get_serializer_class(self):
        """Use detail serializer for retrieve"""
        if self.action == 'retrieve':
            return EstatePlotDetailSerializer
        return EstateSerializer
    
    def perform_create(self, serializer):
        """Create estate with audit log"""
        estate = serializer.save(
            company=self.request.company,
            created_by=self.request.user
        )
        
        AuditLogger.log_create(
            user=self.request.user,
            company=self.request.company,
            instance=estate,
            request=self.request,
            extra_fields=['name', 'location', 'total_plots']
        )
    
    def perform_update(self, serializer):
        """Update estate with audit log"""
        old_instance = self.get_object()
        old_values = {
            'name': old_instance.name,
            'location': old_instance.location,
            'status': old_instance.status,
        }
        
        estate = serializer.save()
        
        new_values = {
            'name': estate.name,
            'location': estate.location,
            'status': estate.status,
        }
        
        AuditLogger.log_update(
            user=self.request.user,
            company=self.request.company,
            instance=estate,
            old_values=old_values,
            new_values=new_values,
            request=self.request,
        )
    
    def perform_destroy(self, instance):
        """Delete estate with audit log"""
        AuditLogger.log_delete(
            user=self.request.user,
            company=self.request.company,
            instance=instance,
            request=self.request,
        )
        instance.delete()
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get estate statistics"""
        
        estate = self.get_object()
        
        stats = {
            'total_plots': estate.estate_plots.count(),
            'allocated_plots': estate.property_allocations.count(),
            'available_plots': estate.estate_plots.filter(
                status='available'
            ).count(),
            'total_value': PropertyPrice.objects.filter(
                plot__estate=estate
            ).aggregate(total=Sum('price'))['total'] or 0,
            'by_status': dict(
                estate.estate_plots.values_list('status').annotate(
                    count=Count('id')
                )
            ),
            'by_plot_size': dict(
                estate.estate_plots.values_list('plot_size__name').annotate(
                    count=Count('id')
                )
            ),
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def allocations(self, request, pk=None):
        """Get estate allocations"""
        
        estate = self.get_object()
        allocations = PlotAllocation.objects.filter(
            plot__estate=estate
        )
        
        serializer = PlotAllocationSerializer(
            allocations,
            many=True
        )
        
        return Response(serializer.data)


class PropertyViewSet(viewsets.ModelViewSet):
    """
    Property management endpoints:
    - List properties
    - Create property
    - Retrieve property details
    - Update property prices
    - Delete property
    """
    
    permission_classes = [
        IsAuthenticated,
        SubscriptionRequiredPermission,
        TenantIsolationPermission,
    ]
    throttle_classes = [SubscriptionTierThrottle]
    serializer_class = EstateSerializer
    filter_backends = [
        CompanyAwareFilterBackend,
        SearchFilterBackend,
        OrderingFilterBackend,
    ]
    search_fields = ['plot__plot_number', 'plot__plot_size__name']
    
    def get_queryset(self):
        """Get properties for user's company"""
        company = getattr(self.request, 'company', None)
        
        if company:
            return EstatePlot.objects.filter(
                estate__company=company
            )
        
        return EstatePlot.objects.none()
    
    def perform_create(self, serializer):
        """Create property with audit log"""
        instance = serializer.save()
        
        AuditLogger.log_create(
            user=self.request.user,
            company=self.request.company,
            instance=instance,
            request=self.request,
            extra_fields=['plot_number', 'plot_size']
        )
    
    def perform_update(self, serializer):
        """Update property with audit log"""
        old_instance = self.get_object()
        old_values = {'status': old_instance.status}
        
        instance = serializer.save()
        new_values = {'status': instance.status}
        
        AuditLogger.log_update(
            user=self.request.user,
            company=self.request.company,
            instance=instance,
            old_values=old_values,
            new_values=new_values,
            request=self.request,
        )
    
    @action(detail=True, methods=['post'])
    def bulk_price_update(self, request, pk=None):
        """Update prices for multiple properties"""
        
        estate = Estate.objects.get(pk=pk)
        
        # Check subscription allows bulk operations
        if not request.user.company.subscription_tier in ['professional', 'enterprise']:
            return Response(
                {'error': 'Bulk operations require Professional tier or higher'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        prices = request.data.get('prices', [])
        
        try:
            with transaction.atomic():
                updated = 0
                
                for price_data in prices:
                    plot_id = price_data.get('plot_id')
                    new_price = price_data.get('price')
                    
                    PropertyPrice.objects.filter(
                        plot_id=plot_id,
                        estate=estate
                    ).update(price=new_price)
                    
                    updated += 1
                
                # Log bulk operation
                AuditLogger.log_bulk_operation(
                    user=request.user,
                    company=request.company,
                    operation_type='price_update',
                    records_affected=updated,
                    request=request
                )
                
                return Response({
                    'message': f'Updated prices for {updated} properties',
                    'updated': updated
                })
        
        except Exception as e:
            logger.error(f"Bulk update error: {e}", exc_info=True)
            ErrorHandler.handle_api_error(e, request=request, view=self)
            return Response(
                {'error': 'Bulk update failed'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PropertyAllocationViewSet(viewsets.ModelViewSet):
    """
    Property allocation endpoints:
    - List allocations
    - Create allocation
    - Update allocation
    - Delete allocation
    - Track payments
    """
    
    permission_classes = [
        IsAuthenticated,
        SubscriptionRequiredPermission,
        TenantIsolationPermission,
    ]
    throttle_classes = [SubscriptionTierThrottle]
    serializer_class = PlotAllocationSerializer
    filter_backends = [
        CompanyAwareFilterBackend,
        SearchFilterBackend,
        OrderingFilterBackend,
        DateRangeFilterBackend,
    ]
    
    def get_queryset(self):
        """Get allocations for user's company"""
        company = getattr(self.request, 'company', None)
        
        if company:
            return PlotAllocation.objects.filter(
                plot__estate__company=company
            )
        
        return PlotAllocation.objects.none()
    
    def perform_create(self, serializer):
        """Create allocation with audit log"""
        allocation = serializer.save()
        
        AuditLogger.log_create(
            user=self.request.user,
            company=self.request.company,
            instance=allocation,
            request=self.request,
            extra_fields=['client', 'plot', 'amount_paid']
        )
    
    def perform_update(self, serializer):
        """Update allocation with audit log"""
        old_instance = self.get_object()
        old_values = {'status': old_instance.status}
        
        allocation = serializer.save()
        new_values = {'status': allocation.status}
        
        AuditLogger.log_update(
            user=self.request.user,
            company=self.request.company,
            instance=allocation,
            old_values=old_values,
            new_values=new_values,
            request=self.request,
        )
    
    def perform_destroy(self, instance):
        """Delete allocation with audit log"""
        AuditLogger.log_delete(
            user=self.request.user,
            company=self.request.company,
            instance=instance,
            request=self.request,
        )
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def record_payment(self, request, pk=None):
        """Record payment for allocation"""
        
        allocation = self.get_object()
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method', 'cash')
        
        if not amount:
            return Response(
                {'error': 'Amount required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Update allocation
            allocation.amount_paid += amount
            allocation.save()
            
            # Log payment
            AuditLogger.log_payment(
                user=request.user,
                company=request.company,
                amount=amount,
                status='SUCCESS',
                transaction_id=None,
                request=request
            )
            
            return Response({
                'message': 'Payment recorded successfully',
                'amount_paid': allocation.amount_paid,
                'balance': allocation.plot.property_price.price - allocation.amount_paid
            })
        
        except Exception as e:
            logger.error(f"Payment recording error: {e}")
            return Response(
                {'error': 'Payment recording failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def payment_history(self, request, pk=None):
        """Get payment history for allocation"""
        
        allocation = self.get_object()
        
        # This would fetch related payment records
        return Response({
            'allocation_id': allocation.id,
            'total_price': allocation.plot.property_price.price,
            'amount_paid': allocation.amount_paid,
            'balance': allocation.plot.property_price.price - allocation.amount_paid,
            'payment_history': []  # Would fetch from Transaction model
        })
    
    @action(detail=False, methods=['post'])
    def bulk_allocate(self, request):
        """Bulk allocate properties to clients"""
        
        # Check subscription allows bulk operations
        company = self.request.company
        if company.subscription_tier not in ['professional', 'enterprise']:
            return Response(
                {'error': 'Bulk operations require Professional tier'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        allocations_data = request.data.get('allocations', [])
        
        try:
            with transaction.atomic():
                created = 0
                
                for alloc_data in allocations_data:
                    PlotAllocation.objects.create(**alloc_data)
                    created += 1
                
                # Log bulk operation
                AuditLogger.log_bulk_operation(
                    user=request.user,
                    company=request.company,
                    operation_type='bulk_allocation',
                    records_affected=created,
                    request=request
                )
                
                return Response({
                    'message': f'Created {created} allocations',
                    'created': created
                })
        
        except Exception as e:
            logger.error(f"Bulk allocation error: {e}")
            ErrorHandler.handle_api_error(e, request=request, view=self)
            return Response(
                {'error': 'Bulk allocation failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
