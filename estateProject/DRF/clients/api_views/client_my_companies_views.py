"""
My Companies Page API Views
============================
API endpoints for the My Companies page (my_companies.html)

Endpoint:
- GET /api/clients/my-companies/ - List companies where client has investments

SECURITY FEATURES:
✅ Token & Session Authentication
✅ IsClient permission with audit logging
✅ Rate limiting (60 requests/hour)
✅ IDOR Protection - client can only see their own companies
✅ No cross-client data exposure
✅ Audit logging for all access
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.throttling import UserRateThrottle
from django.db.models import Sum, Value
from django.db.models.fields import DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
import logging

from DRF.clients.serializers.client_my_companies_serializers import (
    MyCompaniesListResponseSerializer,
    CompanyCardSerializer,
)
from estateApp.models import Company, PlotAllocation, Transaction

logger = logging.getLogger(__name__)


# =============================================================================
# THROTTLE CLASS
# =============================================================================

class MyCompaniesThrottle(UserRateThrottle):
    """Rate limit for My Companies endpoint - 60 requests per hour."""
    rate = '60/hour'


# =============================================================================
# PERMISSION CLASS
# =============================================================================

class IsClient(permissions.BasePermission):
    """
    Permission class to verify user is an authenticated client.
    
    Security Features:
    - Validates user authentication
    - Checks user role is 'client'
    - Allows staff/superuser for debugging
    - Logs access attempts for audit
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            logger.warning(
                f"[SECURITY] Unauthenticated access attempt to {view.__class__.__name__} "
                f"from IP: {self._get_client_ip(request)}"
            )
            return False
        
        # Allow staff/admins for debugging
        if getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False):
            logger.info(f"[AUDIT] Staff/Admin {request.user.email} accessing {view.__class__.__name__}")
            return True
        
        is_client = getattr(request.user, 'role', '') == 'client'
        
        if not is_client:
            logger.warning(
                f"[SECURITY] Non-client user {request.user.email} (role: {getattr(request.user, 'role', 'unknown')}) "
                f"attempted client endpoint access"
            )
        
        return is_client
    
    def _get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_client_ip(request):
    """Extract client IP from request for audit logging."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def get_rank_tag(total_value, plot_count):
    """
    Calculate client rank tag based on total invested value and plot count.
    
    Rank Tiers:
    - Royal Elite: ₦150M+ AND 5+ plots
    - Estate Ambassador: ₦100M+ OR 4+ plots
    - Prime Investor: ₦50M+ OR 3+ plots
    - Smart Owner: ₦20M+ OR 2+ plots
    - First-Time Investor: Default
    """
    tv_num = Decimal(str(total_value)) if total_value else Decimal('0')
    
    if tv_num >= Decimal('150000000') and plot_count >= 5:
        return 'Royal Elite'
    if tv_num >= Decimal('100000000') or plot_count >= 4:
        return 'Estate Ambassador'
    if tv_num >= Decimal('50000000') or plot_count >= 3:
        return 'Prime Investor'
    if tv_num >= Decimal('20000000') or plot_count >= 2:
        return 'Smart Owner'
    return 'First-Time Investor'


# =============================================================================
# MY COMPANIES API VIEW
# =============================================================================

class ClientMyCompaniesAPIView(APIView):
    """
    GET: Returns list of companies where client has investments.
    
    Response matches my_companies.html template requirements:
    - total_companies: Number of companies
    - companies: List of company cards with:
        - id, company_name, logo_url, office_address
        - allocations_count (properties owned)
        - total_invested (₦ amount)
        - rank_tag (Royal Elite, Estate Ambassador, etc.)
    
    SECURITY:
    - Only returns companies where authenticated client has allocations
    - Uses client_id from request.user (IDOR protection)
    - Rate limited to prevent enumeration attacks
    - Audit logged for security monitoring
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    throttle_classes = (MyCompaniesThrottle,)
    
    def get(self, request, *args, **kwargs):
        user = request.user
        client_id = user.id
        
        # Audit log
        logger.info(
            f"[AUDIT] Client {user.email} (ID: {client_id}) accessing My Companies "
            f"from IP: {get_client_ip(request)}"
        )
        
        # SECURITY: Get companies ONLY from client's allocations
        # Uses authenticated user's ID, not from URL/input (IDOR protection)
        company_ids = (
            PlotAllocation.objects.filter(client_id=client_id)
            .values_list('estate__company', flat=True)
            .distinct()
        )
        
        # Filter out None values and get companies
        companies = Company.objects.filter(
            id__in=[c for c in company_ids if c is not None]
        )
        
        # Build company data with metrics (matches template structure)
        company_list = []
        for company in companies:
            # Count allocations for this client in this company
            alloc_count = PlotAllocation.objects.filter(
                client_id=client_id,
                estate__company=company
            ).count()
            
            # Sum total invested from transactions
            total_invested = Transaction.objects.filter(
                client_id=client_id,
                company=company
            ).aggregate(
                total=Coalesce(Sum('total_amount'), Value(0, output_field=DecimalField()))
            )['total'] or Decimal('0')
            
            # Calculate rank tag
            rank_tag = get_rank_tag(total_invested, alloc_count)
            
            company_list.append({
                'id': company.id,
                'company_name': company.company_name,
                'office_address': company.office_address,
                'allocations_count': alloc_count,
                'total_invested': total_invested,
                'rank_tag': rank_tag,
            })
        
        response_data = {
            'total_companies': len(company_list),
            'companies': company_list,
        }
        
        serializer = MyCompaniesListResponseSerializer(response_data, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
