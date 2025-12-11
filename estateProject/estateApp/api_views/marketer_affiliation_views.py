"""
API Views for Marketer Affiliation Management
Allows marketers to manage affiliations with multiple companies
and track their commissions
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Q
from django.utils import timezone

from estateApp.models import (
    MarketerAffiliation, MarketerEarnedCommission, Company, PlotAllocation, CustomUser
)
from estateApp.serializers.company_serializers import (
    MarketerAffiliationSerializer,
    MarketerAffiliationListSerializer,
    MarketerCommissionSerializer,
    CommissionBulkApprovalSerializer
)


class MarketerAffiliationViewSet(viewsets.ModelViewSet):
    """
    Marketer Affiliation Management
    Marketers can affiliate with multiple companies and earn commissions
    
    Endpoints:
    - GET /affiliations/ - List all affiliations for current marketer
    - POST /affiliations/ - Request new affiliation
    - GET /affiliations/{id}/ - Get affiliation details
    - PATCH /affiliations/{id}/ - Update affiliation details
    - POST /affiliations/approve_request/ - Company admin approves affiliation
    """
    serializer_class = MarketerAffiliationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['company', 'status', 'commission_tier']
    search_fields = ['company__company_name', 'marketer__full_name']
    ordering = ['-date_affiliated']
    
    def get_queryset(self):
        """
        Marketers see their own affiliations
        Company admins see all affiliations with their company
        """
        user = self.request.user
        
        if user.role == 'marketer':
            return MarketerAffiliation.objects.filter(marketer=user)
        
        elif user.role == 'admin' and user.company_profile:
            return MarketerAffiliation.objects.filter(company=user.company_profile)
        
        return MarketerAffiliation.objects.none()
    
    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return MarketerAffiliationListSerializer
        return MarketerAffiliationSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Marketer requests affiliation with a company
        Company must approve before marketer can earn commissions
        """
        if request.user.role != 'marketer':
            return Response(
                {'error': 'Only marketers can request affiliations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        company_id = request.data.get('company')
        
        try:
            company = Company.objects.get(id=company_id, is_active=True)
        except Company.DoesNotExist:
            return Response(
                {'error': 'Company not found or inactive'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already affiliated
        existing = MarketerAffiliation.objects.filter(
            marketer=request.user,
            company=company
        ).first()
        
        if existing:
            return Response(
                {'error': f'Already affiliated with {company.company_name}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create affiliation (active immediately since companies add marketers directly)
        affiliation = MarketerAffiliation.objects.create(
            marketer=request.user,
            company=company,
            status='active',
            approval_date=timezone.now(),
            commission_tier=request.data.get('commission_tier', 'bronze'),
            bank_name=request.data.get('bank_name'),
            account_number=request.data.get('account_number'),
            account_name=request.data.get('account_name'),
        )
        
        serializer = self.get_serializer(affiliation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def my_affiliations(self, request):
        """Get all affiliations for current marketer"""
        affiliations = self.get_queryset().filter(marketer=request.user)
        serializer = self.get_serializer(affiliations, many=True)
        
        return Response({
            'total_affiliations': affiliations.count(),
            'active': affiliations.filter(status='active').count(),
            'suspended': affiliations.filter(status='suspended').count(),
            'affiliations': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def active_affiliations(self, request):
        """Get only active affiliations"""
        affiliations = self.get_queryset().filter(status='active')
        serializer = self.get_serializer(affiliations, many=True)
        return Response({
            'total_active': affiliations.count(),
            'affiliations': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """
        Company admin: Get pending affiliation requests
        """
        if request.user.role != 'admin' or not request.user.company_profile:
            return Response(
                {'error': 'Only company admins can view pending approvals'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        pending = MarketerAffiliation.objects.filter(
            company=request.user.company_profile,
            status='pending_approval'
        )
        serializer = self.get_serializer(pending, many=True)
        return Response({
            'pending_count': pending.count(),
            'requests': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Company admin approves a marketer affiliation request
        """
        affiliation = self.get_object()
        
        # Verify permissions
        if request.user.role != 'admin' or request.user.company_profile != affiliation.company:
            return Response(
                {'error': 'Only company admin can approve affiliations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if affiliation.status != 'pending_approval':
            return Response(
                {'error': f'Cannot approve affiliation with status: {affiliation.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        affiliation.status = 'active'
        affiliation.approval_date = timezone.now()
        affiliation.save()
        
        serializer = self.get_serializer(affiliation)
        return Response({
            'message': f'Affiliation approved for {affiliation.marketer.full_name}',
            'affiliation': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Company admin rejects a marketer affiliation request
        """
        affiliation = self.get_object()
        
        if request.user.role != 'admin' or request.user.company_profile != affiliation.company:
            return Response(
                {'error': 'Only company admin can reject affiliations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if affiliation.status != 'pending_approval':
            return Response(
                {'error': 'Can only reject pending requests'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', 'Request rejected by company')
        affiliation.status = 'terminated'
        affiliation.termination_date = timezone.now()
        affiliation.save()
        
        # TODO: Send notification to marketer
        
        return Response({
            'message': 'Affiliation request rejected',
            'reason': reason
        })
    
    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """
        Company admin suspends a marketer affiliation
        """
        affiliation = self.get_object()
        
        if request.user.role != 'admin' or request.user.company_profile != affiliation.company:
            return Response(
                {'error': 'Only company admin can suspend affiliations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reason = request.data.get('reason', 'Suspended by company')
        affiliation.status = 'suspended'
        affiliation.suspension_date = timezone.now()
        affiliation.save()
        
        return Response({
            'message': f'Affiliation suspended',
            'reason': reason
        })
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Company admin reactivates a suspended affiliation
        """
        affiliation = self.get_object()
        
        if request.user.role != 'admin' or request.user.company_profile != affiliation.company:
            return Response(
                {'error': 'Only company admin can activate affiliations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if affiliation.status != 'suspended':
            return Response(
                {'error': 'Can only activate suspended affiliations'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        affiliation.status = 'active'
        affiliation.save()
        
        return Response({'message': 'Affiliation reactivated'})
    
    @action(detail=False, methods=['get'])
    def performance_metrics(self, request):
        """Get performance metrics for marketer's affiliations"""
        if request.user.role != 'marketer':
            return Response(
                {'error': 'Only marketers can view their metrics'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        affiliations = MarketerAffiliation.objects.filter(
            marketer=request.user,
            status='active'
        )
        
        metrics = {
            'total_affiliations': affiliations.count(),
            'total_properties_sold': affiliations.aggregate(
                total=Sum('properties_sold')
            )['total'] or 0,
            'total_commissions_earned': affiliations.aggregate(
                total=Sum('total_commissions_earned')
            )['total'] or 0,
            'total_pending_commissions': affiliations.aggregate(
                total=Sum('total_commissions_earned') - Sum('total_commissions_paid')
            )['total'] or 0,
            'total_commissions_paid': affiliations.aggregate(
                total=Sum('total_commissions_paid')
            )['total'] or 0,
            'by_company': []
        }
        
        for aff in affiliations:
            metrics['by_company'].append({
                'company': aff.company.company_name,
                'commission_tier': aff.get_commission_tier_display(),
                'properties_sold': aff.properties_sold,
                'commissions_earned': str(aff.total_commissions_earned),
                'commissions_paid': str(aff.total_commissions_paid),
                'pending': str(aff.get_pending_commissions()),
            })
        
        return Response(metrics)


class MarketerCommissionViewSet(viewsets.ModelViewSet):
    """
    Commission Tracking and Management
    
    Endpoints:
    - GET /commissions/ - List commissions
    - GET /commissions/pending/ - List pending commissions
    - POST /commissions/approve_bulk/ - Bulk approve commissions
    - POST /commissions/{id}/dispute/ - Dispute a commission
    """
    serializer_class = MarketerCommissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'affiliation__company']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Marketers see their own commissions
        Company admins see all commissions for their company
        """
        user = self.request.user
        
        if user.role == 'marketer':
            return MarketerEarnedCommission.objects.filter(affiliation__marketer=user)
        
        elif user.role == 'admin' and user.company_profile:
            return MarketerEarnedCommission.objects.filter(affiliation__company=user.company_profile)
        
        return MarketerEarnedCommission.objects.none()
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending commissions for approval"""
        commissions = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(commissions, many=True)
        
        total_amount = commissions.aggregate(
            total=Sum('commission_amount')
        )['total'] or 0
        
        return Response({
            'pending_count': commissions.count(),
            'total_amount': str(total_amount),
            'commissions': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def approve_bulk(self, request):
        """
        Bulk approve pending commissions
        Only company admins can approve
        """
        if request.user.role != 'admin' or not request.user.company_profile:
            return Response(
                {'error': 'Only company admins can approve commissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        commission_ids = request.data.get('commission_ids', [])
        
        commissions = MarketerEarnedCommission.objects.filter(
            id__in=commission_ids,
            affiliation__company=request.user.company_profile,
            status='pending'
        )
        
        count = commissions.count()
        commissions.update(status='approved', approved_at=timezone.now())
        
        return Response({
            'message': f'{count} commissions approved',
            'approved_count': count
        })
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """
        Mark commission as paid
        Only company admins can mark commissions as paid
        """
        commission = self.get_object()
        
        if request.user.role != 'admin' or request.user.company_profile != commission.affiliation.company:
            return Response(
                {'error': 'Only company admin can mark commissions as paid'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if commission.status != 'approved':
            return Response(
                {'error': 'Only approved commissions can be marked as paid'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment_reference = request.data.get('payment_reference')
        commission.mark_as_paid(payment_reference)
        
        serializer = self.get_serializer(commission)
        return Response({
            'message': 'Commission marked as paid',
            'commission': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def dispute(self, request, pk=None):
        """
        Dispute a commission
        Marketers can dispute pending/approved commissions
        """
        commission = self.get_object()
        
        if request.user.role == 'marketer':
            if commission.affiliation.marketer != request.user:
                return Response(
                    {'error': 'Cannot dispute another marketer\'s commission'},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif request.user.role == 'admin':
            if commission.affiliation.company != request.user.company_profile:
                return Response(
                    {'error': 'Cannot dispute commission from another company'},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reason = request.data.get('reason')
        if not reason:
            return Response(
                {'error': 'Dispute reason required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        commission.status = 'disputed'
        commission.dispute_reason = reason
        commission.disputed_at = timezone.now()
        commission.save()
        
        # TODO: Send notification to both parties
        
        serializer = self.get_serializer(commission)
        return Response({
            'message': 'Commission disputed',
            'commission': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get commission summary for current user"""
        commissions = self.get_queryset()
        
        summary = {
            'total_earned': str(commissions.aggregate(
                total=Sum('commission_amount')
            )['total'] or 0),
            'total_paid': str(commissions.filter(status='paid').aggregate(
                total=Sum('commission_amount')
            )['total'] or 0),
            'pending_approval': commissions.filter(status='pending').count(),
            'approved': commissions.filter(status='approved').count(),
            'paid': commissions.filter(status='paid').count(),
            'disputed': commissions.filter(status='disputed').count(),
        }
        
        return Response(summary)
