"""
Marketer Affiliation Request System
Allows marketers to request affiliation with any company on the platform
and companies to approve/reject these requests
"""
from django.db.models import Q, Count, Sum
from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from DRF.shared_drf.api_response import APIResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from django.shortcuts import get_object_or_404
from decimal import Decimal

from estateApp.models import (
    CustomUser, MarketerAffiliation, Company, 
    Notification, UserNotification
)
from DRF.marketers.serializers.permissions import IsMarketerUser


class AvailableCompaniesAPIView(APIView):
    """
    GET /api/marketer/available-companies/
    Returns list of companies marketer can request to affiliate with
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)

    def get(self, request):
        user = request.user
        
        # Get companies marketer is already affiliated with (any status)
        affiliated_company_ids = MarketerAffiliation.objects.filter(
            marketer=user
        ).values_list('company_id', flat=True)
        
        # Get all active companies excluding those already affiliated
        available_companies = Company.objects.filter(
            is_active=True
        ).exclude(
            id__in=affiliated_company_ids
        ).annotate(
            marketers_count=Count('marketer_affiliations', filter=Q(marketer_affiliations__status='active'))
        ).values(
            'id', 'company_name', 'logo', 'email', 'phone', 
            'location', 'office_address', 'marketers_count'
        ).order_by('company_name')
        
        companies_list = []
        for company in available_companies:
            companies_list.append({
                'id': company['id'],
                'name': company['company_name'],
                'logo': request.build_absolute_uri(company['logo']) if company['logo'] else None,
                'email': company['email'],
                'phone': company['phone'],
                'location': company['location'],
                'office_address': company['office_address'],
                'marketers_count': company['marketers_count'] or 0,
            })
        
        return APIResponse.success(
            data={
                'companies': companies_list,
                'total_companies': len(companies_list),
            },
            message='Available companies retrieved',
        )


class RequestAffiliationAPIView(APIView):
    """
    POST /api/marketer/request-affiliation/
    Allows marketer to request affiliation with a company
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)

    def post(self, request):
        user = request.user
        company_id = request.data.get('company_id')
        
        if not company_id:
            return APIResponse.validation_error({'company_id': ['Company ID is required']})
        
        # Verify company exists
        company = get_object_or_404(Company, id=company_id, is_active=True)
        
        # Check if affiliation already exists
        existing = MarketerAffiliation.objects.filter(
            marketer=user,
            company=company
        ).first()
        
        if existing:
            return APIResponse.error(
                message=f'You already have an affiliation with {company.company_name} (Status: {existing.get_status_display()})',
                status_code=400,
                error_code='ALREADY_AFFILIATED',
            )
        
        # Create affiliation (active immediately since companies add marketers directly)
        with transaction.atomic():
            affiliation = MarketerAffiliation.objects.create(
                marketer=user,
                company=company,
                status='active',
                approval_date=timezone.now(),
                commission_tier='bronze',  # Default tier
                commission_rate=Decimal('2.0')  # Default 2%
            )
            
            # Create notification for company admins
            notification = Notification.objects.create(
                company=company,
                title='New Marketer Added',
                message=f'{user.full_name} has been added as an affiliate marketer for your company.',
                notification_type=Notification.COMPANY_ANNOUNCEMENT,
                priority='high'
            )
            
            # Notify all company admins
            company_admins = CustomUser.objects.filter(
                company_profile=company,
                role='admin'
            )
            
            for admin in company_admins:
                UserNotification.objects.create(
                    user=admin,
                    notification=notification
                )
        
        return APIResponse.created(
            data={
                'affiliation': {
                    'id': affiliation.id,
                    'company_name': company.company_name,
                    'status': affiliation.status,
                    'date_requested': affiliation.date_affiliated.isoformat(),
                }
            },
            message=f'Affiliation request sent to {company.company_name}. You will be notified once they review your request.',
        )


class MarketerAffiliationsAPIView(APIView):
    """
    GET /api/marketer/affiliations/
    Returns all affiliations for the authenticated marketer
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)

    def get(self, request):
        user = request.user
        
        # Get all affiliations
        affiliations = MarketerAffiliation.objects.filter(
            marketer=user
        ).select_related('company').order_by('-date_affiliated')
        
        affiliations_list = []
        for affiliation in affiliations:
            affiliations_list.append({
                'id': affiliation.id,
                'company': {
                    'id': affiliation.company.id,
                    'name': affiliation.company.company_name,
                    'logo': request.build_absolute_uri(affiliation.company.logo.url) if affiliation.company.logo else None,
                    'email': affiliation.company.email,
                    'phone': affiliation.company.phone,
                },
                'status': affiliation.status,
                'status_display': affiliation.get_status_display(),
                'commission_tier': affiliation.get_commission_tier_display(),
                'commission_rate': str(affiliation.commission_rate),
                'properties_sold': affiliation.properties_sold,
                'total_commissions_earned': str(affiliation.total_commissions_earned),
                'total_commissions_paid': str(affiliation.total_commissions_paid),
                'pending_commissions': str(affiliation.get_pending_commissions()),
                'total_sales_value': str(affiliation.total_sales_value),
                'date_affiliated': affiliation.date_affiliated.isoformat(),
                'approval_date': affiliation.approval_date.isoformat() if affiliation.approval_date else None,
            })
        
        # Group by status
        active = [a for a in affiliations_list if a['status'] == 'active']
        pending = [a for a in affiliations_list if a['status'] == 'pending_approval']
        suspended = [a for a in affiliations_list if a['status'] == 'suspended']
        terminated = [a for a in affiliations_list if a['status'] == 'terminated']
        
        return APIResponse.success(
            data={
                'affiliations': affiliations_list,
                'summary': {
                    'total': len(affiliations_list),
                    'active': len(active),
                    'pending': len(pending),
                    'suspended': len(suspended),
                    'terminated': len(terminated),
                },
                'grouped': {
                    'active': active,
                    'pending': pending,
                    'suspended': suspended,
                    'terminated': terminated,
                },
            },
            message='Affiliations retrieved',
        )


class CancelAffiliationRequestAPIView(APIView):
    """
    DELETE /api/marketer/affiliations/<affiliation_id>/cancel/
    Allows marketer to cancel a pending affiliation request
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)

    def delete(self, request, affiliation_id):
        user = request.user
        
        # Get affiliation
        affiliation = get_object_or_404(
            MarketerAffiliation,
            id=affiliation_id,
            marketer=user
        )
        
        # Only pending requests can be cancelled
        if affiliation.status != 'pending_approval':
            return APIResponse.bad_request('Only pending affiliation requests can be cancelled')
        
        company_name = affiliation.company.company_name
        affiliation.delete()
        
        return APIResponse.success(
            data={'company_name': company_name},
            message=f'Affiliation request with {company_name} has been cancelled',
        )


# ============================================================================
# COMPANY ADMIN VIEWS - For managing affiliation requests
# ============================================================================

class PendingAffiliationRequestsAPIView(APIView):
    """
    GET /api/admin/affiliation-requests/
    Returns pending affiliation requests for the company admin's company
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        
        # Verify user is admin
        if user.role != 'admin':
            return APIResponse.forbidden('Only company administrators can access this endpoint')
        
        # Get user's company
        company = user.company_profile
        if not company:
            return APIResponse.bad_request('No company associated with your account')
        
        # Get pending affiliations
        pending_requests = MarketerAffiliation.objects.filter(
            company=company,
            status='pending_approval'
        ).select_related('marketer').order_by('-date_affiliated')
        
        requests_list = []
        for affiliation in pending_requests:
            requests_list.append({
                'id': affiliation.id,
                'marketer': {
                    'id': affiliation.marketer.id,
                    'name': affiliation.marketer.full_name,
                    'email': affiliation.marketer.email,
                    'phone': affiliation.marketer.phone,
                    'profile_image': request.build_absolute_uri(affiliation.marketer.profile_image.url) if affiliation.marketer.profile_image else None,
                },
                'date_requested': affiliation.date_affiliated.isoformat(),
                'days_pending': (timezone.now() - affiliation.date_affiliated).days,
            })
        
        return APIResponse.success(
            data={'requests': requests_list, 'total_pending': len(requests_list)},
            message='Pending affiliation requests retrieved',
        )


class ApproveAffiliationRequestAPIView(APIView):
    """
    POST /api/admin/affiliation-requests/<affiliation_id>/approve/
    Approve a marketer's affiliation request
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

    def post(self, request, affiliation_id):
        user = request.user
        
        # Verify user is admin
        if user.role != 'admin':
            return APIResponse.forbidden('Only company administrators can approve affiliations')
        
        company = user.company_profile
        if not company:
            return APIResponse.bad_request('No company associated with your account')
        
        # Get affiliation
        affiliation = get_object_or_404(
            MarketerAffiliation,
            id=affiliation_id,
            company=company
        )
        
        if affiliation.status != 'pending_approval':
            return APIResponse.bad_request('This affiliation request has already been processed')
        
        # Optional: Set commission tier and rate from request
        commission_tier = request.data.get('commission_tier', 'bronze')
        commission_rates = {
            'bronze': Decimal('2.0'),
            'silver': Decimal('3.5'),
            'gold': Decimal('5.0'),
            'platinum': Decimal('7.0'),
        }
        
        with transaction.atomic():
            # Approve affiliation
            affiliation.status = 'active'
            affiliation.approval_date = timezone.now()
            affiliation.commission_tier = commission_tier
            affiliation.commission_rate = commission_rates.get(commission_tier, Decimal('2.0'))
            affiliation.save()
            
            # Notify marketer
            notification = Notification.objects.create(
                company=company,
                title='Affiliation Request Approved! 🎉',
                message=f'Congratulations! {company.company_name} has approved your affiliation request. You can now start earning commissions on property sales.',
                notification_type=Notification.MARKETER_ANNOUNCEMENT,
                priority='high'
            )
            
            UserNotification.objects.create(
                user=affiliation.marketer,
                notification=notification
            )
        
        return APIResponse.success(
            data={
                'affiliation': {
                    'id': affiliation.id,
                    'marketer_name': affiliation.marketer.full_name,
                    'status': affiliation.status,
                    'commission_tier': affiliation.get_commission_tier_display(),
                    'commission_rate': str(affiliation.commission_rate),
                    'approval_date': affiliation.approval_date.isoformat(),
                }
            },
            message=f'{affiliation.marketer.full_name} has been approved as an affiliate marketer',
        )


class RejectAffiliationRequestAPIView(APIView):
    """
    POST /api/admin/affiliation-requests/<affiliation_id>/reject/
    Reject a marketer's affiliation request
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

    def post(self, request, affiliation_id):
        user = request.user
        
        # Verify user is admin
        if user.role != 'admin':
            return APIResponse.forbidden('Only company administrators can reject affiliations')
        
        company = user.company_profile
        if not company:
            return APIResponse.bad_request('No company associated with your account')
        
        # Get affiliation
        affiliation = get_object_or_404(
            MarketerAffiliation,
            id=affiliation_id,
            company=company
        )
        
        if affiliation.status != 'pending_approval':
            return APIResponse.bad_request('This affiliation request has already been processed')
        
        marketer_name = affiliation.marketer.full_name
        marketer = affiliation.marketer
        
        with transaction.atomic():
            # Delete the affiliation request
            affiliation.delete()
            
            # Notify marketer
            notification = Notification.objects.create(
                company=company,
                title='Affiliation Request Not Approved',
                message=f'Thank you for your interest in {company.company_name}. Unfortunately, your affiliation request was not approved at this time. You may reapply in the future.',
                notification_type=Notification.MARKETER_ANNOUNCEMENT,
                priority='normal'
            )
            
            UserNotification.objects.create(
                user=marketer,
                notification=notification
            )
        
        return APIResponse.success(
            data={'marketer_name': marketer_name},
            message=f'Affiliation request from {marketer_name} has been rejected',
        )


class CompanyAffiliatedMarketersAPIView(APIView):
    """
    GET /api/admin/affiliated-marketers/
    Returns list of all active affiliate marketers for the company
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        
        # Verify user is admin
        if user.role != 'admin':
            return APIResponse.forbidden('Only company administrators can access this endpoint')
        
        company = user.company_profile
        if not company:
            return APIResponse.bad_request('No company associated with your account')
        
        # Get active affiliations
        affiliations = MarketerAffiliation.objects.filter(
            company=company,
            status='active'
        ).select_related('marketer').order_by('-total_sales_value')
        
        marketers_list = []
        for affiliation in affiliations:
            marketers_list.append({
                'id': affiliation.id,
                'marketer': {
                    'id': affiliation.marketer.id,
                    'name': affiliation.marketer.full_name,
                    'email': affiliation.marketer.email,
                    'phone': affiliation.marketer.phone,
                },
                'commission_tier': affiliation.get_commission_tier_display(),
                'commission_rate': str(affiliation.commission_rate),
                'properties_sold': affiliation.properties_sold,
                'total_sales_value': str(affiliation.total_sales_value),
                'total_commissions_earned': str(affiliation.total_commissions_earned),
                'pending_commissions': str(affiliation.get_pending_commissions()),
                'date_affiliated': affiliation.date_affiliated.isoformat(),
                'approval_date': affiliation.approval_date.isoformat() if affiliation.approval_date else None,
            })
        
        return APIResponse.success(
            data={
                'marketers': marketers_list,
                'total_marketers': len(marketers_list),
                'total_sales': str(sum(Decimal(m['total_sales_value']) for m in marketers_list)),
                'total_commissions': str(sum(Decimal(m['total_commissions_earned']) for m in marketers_list)),
            },
            message='Affiliated marketers retrieved',
        )
