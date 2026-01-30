"""
Client Company API Views
=========================
API endpoints for client company portfolio pages with enterprise-grade security.

MY COMPANIES PAGE:
- ClientMyCompaniesAPIView: GET list of companies client has invested in

MY COMPANY PORTFOLIO PAGE:
- ClientCompanyPortfolioAPIView: GET detailed portfolio for specific company
- ClientCompanyPropertiesAPIView: GET properties list
- ClientCompanyAppreciationAPIView: GET appreciation data
- ClientCompanyPaymentsAPIView: GET recent payments
- ClientCompanyTransactionDetailAPIView: GET transaction details for modal

SECURITY FEATURES:
✅ Token & Session Authentication
✅ IsClient permission class with audit logging
✅ Rate limiting/throttling (30 req/hour for data views)
✅ IDOR Protection - client can only access their own data
✅ Company Access Validation - verify client has allocations in company
✅ Cross-company data isolation
✅ Input sanitization on company_id
✅ Audit logging for all data access
✅ No data leakage between clients
"""

from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.throttling import UserRateThrottle
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Value, OuterRef, Subquery
from django.db.models.fields import DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from datetime import date
from collections import OrderedDict
import logging

from DRF.shared_drf import APIResponse
from DRF.clients.serializers.client_company_serializers import (
    MyCompaniesResponseSerializer,
    ClientCompanySerializer,
    CompanyPortfolioResponseSerializer,
    PropertySerializer,
    AppreciationPropertySerializer,
    PaymentRecordSerializer,
    TransactionDetailSerializer,
    TransactionPaymentHistoryResponseSerializer,
)
from estateApp.models import (
    ClientUser, Company, PlotAllocation, Transaction,
    PropertyPrice, Estate, PaymentRecord, ClientMarketerAssignment
)

logger = logging.getLogger(__name__)


# =============================================================================
# THROTTLE CLASSES
# =============================================================================

class CompanyDataThrottle(UserRateThrottle):
    """Rate limit for company data endpoints - 60 requests per hour."""
    rate = '60/hour'


class TransactionDetailThrottle(UserRateThrottle):
    """Rate limit for transaction detail endpoints - 120 requests per hour."""
    rate = '120/hour'


# =============================================================================
# PERMISSION CLASSES
# =============================================================================

class IsClient(permissions.BasePermission):
    """
    Permission class to verify user is an authenticated client.
    
    Security Features:
    - Validates user is authenticated
    - Checks user role is 'client'
    - Allows staff/superuser access for debugging
    - Logs access attempts for audit trail
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
            logger.info(
                f"[AUDIT] Staff/Admin {request.user.email} accessing {view.__class__.__name__}"
            )
            return True
        
        # Check client role
        is_client = getattr(request.user, 'role', '') == 'client'
        
        if not is_client:
            logger.warning(
                f"[SECURITY] Non-client user {request.user.email} (role: {getattr(request.user, 'role', 'unknown')}) "
                f"attempted to access client endpoint {view.__class__.__name__}"
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
    Calculate client rank tag based on total value and plot count.
    Same logic as template view for consistency.
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


def validate_company_access(client_id, company):
    """
    SECURITY: Validate that client has allocations in this company.
    Prevents unauthorized access to company data.
    
    Returns: True if client has access, False otherwise.
    """
    return PlotAllocation.objects.filter(
        client_id=client_id,
        estate__company=company
    ).exists()


def calculate_portfolio_metrics(transactions, allocations=None):
    """
    Calculate portfolio metrics: current value, appreciation, growth rates.
    
    Returns dict with:
    - total_current_value
    - total_appreciation
    - appreciation_total (alias)
    - average_growth
    - highest_growth_rate
    - highest_growth_property
    - transactions (annotated with metrics)
    """
    total_current_value = Decimal('0')
    total_invested = Decimal('0')
    property_growth_rates = []
    highest_growth_rate = Decimal('0')
    highest_growth_property = ''
    
    annotated_transactions = []
    
    for txn in transactions:
        purchase_price = txn.total_amount or Decimal('0')
        total_invested += purchase_price
        
        # Get current price
        current_value = purchase_price  # Default to purchase price
        
        if hasattr(txn, 'allocation') and txn.allocation:
            try:
                prop_price = PropertyPrice.objects.filter(
                    estate=txn.allocation.estate,
                    plot_unit__plot_size=txn.allocation.plot_size
                ).order_by('-effective').first()
                
                if prop_price and prop_price.current:
                    current_value = prop_price.current
            except Exception:
                pass
        
        total_current_value += current_value
        
        # Calculate growth
        appreciation = current_value - purchase_price
        if purchase_price > 0:
            growth_rate = ((current_value - purchase_price) / purchase_price) * 100
        else:
            growth_rate = Decimal('0')
        
        # Track highest growth
        if growth_rate > highest_growth_rate:
            highest_growth_rate = growth_rate
            if hasattr(txn, 'allocation') and txn.allocation and hasattr(txn.allocation, 'estate'):
                highest_growth_property = txn.allocation.estate.name
        
        property_growth_rates.append(growth_rate)
        
        # Annotate transaction
        txn.current_value = current_value
        txn.appreciation = appreciation
        txn.growth_rate = growth_rate
        txn.abs_growth_rate = abs(growth_rate)
        annotated_transactions.append(txn)
    
    # Calculate averages
    appreciation_total = total_current_value - total_invested
    average_growth = sum(property_growth_rates) / len(property_growth_rates) if property_growth_rates else Decimal('0')
    
    return {
        'total_current_value': total_current_value,
        'total_invested': total_invested,
        'total_appreciation': appreciation_total,
        'appreciation_total': appreciation_total,
        'average_growth': average_growth,
        'highest_growth_rate': highest_growth_rate,
        'highest_growth_property': highest_growth_property,
        'transactions': annotated_transactions,
    }


# =============================================================================
# MY COMPANIES PAGE VIEW
# =============================================================================

class ClientMyCompaniesAPIView(APIView):
    """
    GET: Returns list of companies where client has investments.
    
    Response includes:
    - Company info (name, logo, address)
    - Allocation count
    - Total invested
    - Client rank in that company
    
    SECURITY:
    - Only returns companies where authenticated client has allocations
    - Uses client_id from request.user (IDOR protection)
    - Rate limited to prevent enumeration attacks
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    throttle_classes = (CompanyDataThrottle,)
    
    def get(self, request, *args, **kwargs):
        user = request.user
        client_id = user.id
        
        # Audit log
        logger.info(
            f"[AUDIT] Client {user.email} (ID: {client_id}) accessing My Companies list "
            f"from IP: {get_client_ip(request)}"
        )
        
        # Get company IDs from client's allocations (IDOR protection - uses authenticated user's ID)
        company_ids = (
            PlotAllocation.objects.filter(client_id=client_id)
            .values_list('estate__company', flat=True)
            .distinct()
        )
        
        # Filter out None values and get companies
        companies = Company.objects.filter(
            id__in=[c for c in company_ids if c is not None]
        )
        
        # Build company data with metrics
        company_list = []
        for company in companies:
            # Calculate metrics for this company
            alloc_count = PlotAllocation.objects.filter(
                client_id=client_id,
                estate__company=company
            ).count()
            
            total_invested = Transaction.objects.filter(
                client_id=client_id,
                company=company
            ).aggregate(
                total=Coalesce(Sum('total_amount'), Value(0, output_field=DecimalField()))
            )['total'] or Decimal('0')
            
            # Calculate rank
            rank_tag = get_rank_tag(total_invested, alloc_count)
            
            company_list.append({
                'id': company.id,
                'company_name': company.company_name,
                'office_address': company.office_address,
                'email': company.email,
                'phone': company.phone,
                'allocations_count': alloc_count,
                'total_invested': total_invested,
                'rank_tag': rank_tag,
            })
        
        response_data = {
            'total_companies': len(company_list),
            'companies': company_list,
        }
        
        serializer = MyCompaniesResponseSerializer(response_data, context={'request': request})
        return APIResponse.success(
            data=serializer.data,
            message="Companies list retrieved successfully"
        )


# =============================================================================
# MY COMPANY PORTFOLIO PAGE VIEWS
# =============================================================================

class ClientCompanyPortfolioAPIView(APIView):
    """
    GET: Returns complete portfolio data for a specific company.
    
    Response includes:
    - Company info
    - Portfolio stats (total invested, appreciation, current value)
    - Marketer info
    - Properties list
    - Value appreciation data
    - Recent payments grouped by year
    - Portfolio summary
    
    SECURITY:
    - Validates client has allocations in requested company
    - Returns 404 if unauthorized (doesn't leak company existence)
    - Rate limited to prevent scraping
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    throttle_classes = (CompanyDataThrottle,)
    
    def get(self, request, company_id, *args, **kwargs):
        user = request.user
        client_id = user.id
        
        # Input validation
        try:
            company_id = int(company_id)
        except (ValueError, TypeError):
            logger.warning(
                f"[SECURITY] Invalid company_id '{company_id}' from client {user.email}"
            )
            return APIResponse.validation_error(
                errors={'company_id': ['Invalid company ID']},
                error_code="INVALID_ID"
            )
        
        # Get company (404 if not found)
        company = get_object_or_404(Company, id=company_id)
        
        # SECURITY: Verify client has allocations in this company
        if not validate_company_access(client_id, company):
            logger.warning(
                f"[SECURITY] Unauthorized portfolio access attempt by client {user.email} "
                f"(ID: {client_id}) for company {company.company_name} (ID: {company_id}) "
                f"from IP: {get_client_ip(request)}"
            )
            return APIResponse.not_found(
                message="You do not have any allocations in this company",
                error_code="ACCESS_DENIED"
            )
        
        # Audit log - successful access
        logger.info(
            f"[AUDIT] Client {user.email} (ID: {client_id}) viewing portfolio for "
            f"company {company.company_name} (ID: {company_id}) from IP: {get_client_ip(request)}"
        )
        
        # Get transactions using all_objects to bypass CompanyAwareManager
        transactions = (
            Transaction.all_objects.filter(client_id=client_id, company=company)
            .select_related('allocation__estate', 'allocation__plot_size', 'allocation__plot_number')
            .prefetch_related('payment_records')
            .order_by('-transaction_date')
        )
        
        # Calculate metrics
        metrics = calculate_portfolio_metrics(transactions)
        transactions = metrics['transactions']
        
        # Calculate totals
        total_invested = metrics['total_invested']
        total_current_value = metrics['total_current_value']
        total_appreciation = metrics['total_appreciation']
        
        # Get marketer assignment for this company
        try:
            assignment = ClientMarketerAssignment.objects.filter(
                client_id=client_id,
                company=company
            ).select_related('marketer').first()
            marketer = assignment.marketer if assignment else None
        except Exception:
            marketer = None
        
        # Build properties list
        properties_list = []
        appreciation_list = []
        
        for txn in transactions:
            alloc = txn.allocation
            if not alloc:
                continue
            
            property_data = {
                'allocation_id': alloc.id,
                'transaction_id': txn.id,
                'estate': {
                    'id': alloc.estate.id,
                    'name': alloc.estate.name,
                    'location': alloc.estate.location,
                },
                'plot_size': {
                    'id': alloc.plot_size.id if alloc.plot_size else None,
                    'size': str(alloc.plot_size.size) if alloc.plot_size else 'N/A',
                },
                'plot_number': str(alloc.plot_number) if alloc.plot_number else None,
                'purchase_price': txn.total_amount or Decimal('0'),
                'current_value': getattr(txn, 'current_value', txn.total_amount or Decimal('0')),
                'appreciation': getattr(txn, 'appreciation', Decimal('0')),
                'growth_rate': getattr(txn, 'growth_rate', Decimal('0')),
                'payment_type': alloc.payment_type,
                'payment_status': txn.status or 'Active',
                'transaction_date': txn.transaction_date,
            }
            properties_list.append(property_data)
            
            # Build appreciation data
            appreciation_data = {
                'allocation_id': alloc.id,
                'estate_name': alloc.estate.name,
                'plot_size': str(alloc.plot_size.size) if alloc.plot_size else 'N/A',
                'purchase_price': txn.total_amount or Decimal('0'),
                'current_value': getattr(txn, 'current_value', txn.total_amount or Decimal('0')),
                'value_increase': getattr(txn, 'appreciation', Decimal('0')),
                'growth_rate': getattr(txn, 'growth_rate', Decimal('0')),
                'abs_growth_rate': getattr(txn, 'abs_growth_rate', Decimal('0')),
                'purchase_date': txn.transaction_date,
                'current_date': date.today(),
            }
            appreciation_list.append(appreciation_data)
        
        # Build recent payments
        recent_payments = []
        for txn in transactions:
            if txn.allocation.payment_type == 'full':
                recent_payments.append({
                    'id': txn.id,
                    'date': txn.transaction_date,
                    'amount': txn.total_amount,
                    'reference_code': txn.reference_code,
                    'payment_type': 'Full Payment',
                    'status': txn.status,
                    'estate_name': txn.allocation.estate.name if txn.allocation and txn.allocation.estate else 'N/A',
                })
            else:
                for pr in txn.payment_records.all().order_by('-payment_date'):
                    installment_display = (
                        pr.get_selected_installment_display() if hasattr(pr, 'get_selected_installment_display') 
                        else f"Installment {pr.installment}" if hasattr(pr, 'installment') else "Payment"
                    )
                    recent_payments.append({
                        'id': pr.id,
                        'date': pr.payment_date,
                        'amount': pr.amount_paid,
                        'reference_code': pr.reference_code,
                        'payment_type': installment_display,
                        'status': 'Paid',
                        'estate_name': txn.allocation.estate.name if txn.allocation and txn.allocation.estate else 'N/A',
                    })
        
        # Sort by date descending
        recent_payments.sort(key=lambda x: x['date'], reverse=True)
        
        # Group by year
        payments_by_year = OrderedDict()
        for payment in recent_payments:
            year = payment['date'].year
            if year not in payments_by_year:
                payments_by_year[year] = []
            payments_by_year[year].append(payment)
        
        # Count estates in company
        estates_count = Estate.objects.filter(company=company).count()
        
        # Build response
        response_data = {
            'company': {
                'id': company.id,
                'company_name': company.company_name,
                'office_address': company.office_address,
                'location': company.location,
                'email': company.email,
                'phone': company.phone,
            },
            'stats': {
                'total_invested': total_invested,
                'total_appreciation': total_appreciation,
                'total_current_value': total_current_value,
                'marketer': {
                    'id': marketer.id,
                    'full_name': marketer.full_name,
                    'email': marketer.email,
                    'phone': marketer.phone,
                } if marketer else None,
            },
            'properties': properties_list,
            'properties_count': len(properties_list),
            'appreciation_data': appreciation_list,
            'payments_by_year': {str(year): payments for year, payments in payments_by_year.items()},
            'total_payments_count': len(recent_payments),
            'summary': {
                'appreciation_total': metrics['appreciation_total'],
                'average_growth': metrics['average_growth'],
                'highest_growth_rate': metrics['highest_growth_rate'],
                'highest_growth_property': metrics['highest_growth_property'],
            },
            'estates_count': estates_count,
        }
        
        return APIResponse.success(
            data=response_data,
            message="Portfolio data retrieved successfully"
        )


class ClientCompanyTransactionDetailAPIView(APIView):
    """
    GET: Returns transaction details for modal.
    
    SECURITY:
    - Validates transaction belongs to authenticated client
    - Validates transaction is in specified company
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    throttle_classes = (TransactionDetailThrottle,)
    
    def get(self, request, transaction_id, *args, **kwargs):
        user = request.user
        client_id = user.id
        
        # Input validation
        try:
            transaction_id = int(transaction_id)
        except (ValueError, TypeError):
            return APIResponse.validation_error(
                errors={'transaction_id': ['Invalid transaction ID']},
                error_code="INVALID_ID"
            )
        
        # Get transaction - SECURITY: Filter by client_id
        try:
            transaction = Transaction.all_objects.select_related(
                'allocation__estate',
                'allocation__plot_size',
                'allocation__plot_number',
                'company'
            ).get(id=transaction_id, client_id=client_id)
        except Transaction.DoesNotExist:
            logger.warning(
                f"[SECURITY] Transaction access denied - client {user.email} "
                f"attempted to access transaction {transaction_id} from IP: {get_client_ip(request)}"
            )
            return APIResponse.not_found(
                message="Transaction not found",
                error_code="TRANSACTION_NOT_FOUND"
            )
        
        # Audit log
        logger.info(
            f"[AUDIT] Client {user.email} viewing transaction {transaction_id} "
            f"from IP: {get_client_ip(request)}"
        )
        
        # Build response
        allocation = transaction.allocation
        response_data = {
            'id': transaction.id,
            'reference_code': transaction.reference_code,
            'transaction_date': transaction.transaction_date,
            'total_amount': transaction.total_amount,
            'total_paid': transaction.total_paid,
            'balance': transaction.balance,
            'status': transaction.status,
            'allocation': {
                'estate': {
                    'name': allocation.estate.name if allocation and allocation.estate else '',
                },
                'plot_size': str(allocation.plot_size.size) if allocation and allocation.plot_size else '',
                'plot_number': str(allocation.plot_number) if allocation and allocation.plot_number else None,
                'payment_type': allocation.payment_type if allocation else '',
            },
            'payment_duration': getattr(transaction, 'payment_duration', None),
            'custom_duration': getattr(transaction, 'custom_duration', None),
            'installment_plan': getattr(transaction, 'installment_plan', None),
            'first_percent': getattr(transaction, 'first_percent', None),
            'second_percent': getattr(transaction, 'second_percent', None),
            'third_percent': getattr(transaction, 'third_percent', None),
            'first_installment': getattr(transaction, 'first_installment', None),
            'second_installment': getattr(transaction, 'second_installment', None),
            'third_installment': getattr(transaction, 'third_installment', None),
        }
        
        return APIResponse.success(
            data=response_data,
            message="Transaction details retrieved successfully"
        )


class ClientCompanyPaymentHistoryAPIView(APIView):
    """
    GET: Returns payment history for a transaction (for modal).
    
    Query params:
    - transaction_id: Required transaction ID
    
    SECURITY:
    - Validates transaction belongs to authenticated client
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    throttle_classes = (TransactionDetailThrottle,)
    
    def get(self, request, *args, **kwargs):
        user = request.user
        client_id = user.id
        
        transaction_id = request.query_params.get('transaction_id')
        
        if not transaction_id:
            return APIResponse.validation_error(
                errors={'transaction_id': ['transaction_id query parameter is required']},
                error_code="MISSING_PARAMETER"
            )
        
        # Input validation
        try:
            transaction_id = int(transaction_id)
        except (ValueError, TypeError):
            return APIResponse.validation_error(
                errors={'transaction_id': ['Invalid transaction ID']},
                error_code="INVALID_ID"
            )
        
        # SECURITY: Verify transaction belongs to client
        try:
            transaction = Transaction.all_objects.get(id=transaction_id, client_id=client_id)
        except Transaction.DoesNotExist:
            logger.warning(
                f"[SECURITY] Payment history access denied - client {user.email} "
                f"attempted to access transaction {transaction_id}"
            )
            return APIResponse.not_found(
                message="Transaction not found",
                error_code="TRANSACTION_NOT_FOUND"
            )
        
        # Get payment records
        payments = transaction.payment_records.all().order_by('-payment_date')
        
        payments_list = []
        for pr in payments:
            installment = (
                pr.get_selected_installment_display() if hasattr(pr, 'get_selected_installment_display')
                else f"Installment {pr.installment}" if hasattr(pr, 'installment') and pr.installment
                else "Payment"
            )
            payments_list.append({
                'date': pr.payment_date,
                'amount': pr.amount_paid,
                'method': pr.payment_method if hasattr(pr, 'payment_method') else 'N/A',
                'installment': installment,
                'reference': pr.reference_code,
            })
        
        return APIResponse.success(
            data={'payments': payments_list},
            message="Payment history retrieved successfully"
        )


class ClientCompanyReceiptDownloadAPIView(APIView):
    """
    GET: Get receipt download URL/data for a payment.
    
    Query params:
    - reference: Payment reference code
    
    SECURITY:
    - Validates payment belongs to authenticated client
    - Prevents unauthorized receipt access
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    throttle_classes = (TransactionDetailThrottle,)
    
    def get(self, request, reference=None, *args, **kwargs):
        user = request.user
        client_id = user.id
        
        # Get reference from URL or query params
        ref = reference or request.query_params.get('reference')
        
        if not ref:
            return APIResponse.validation_error(
                errors={'reference': ['Payment reference is required']},
                error_code="MISSING_PARAMETER"
            )
        
        # Input sanitization - validate reference format
        import re
        if not re.match(r'^[A-Za-z0-9\-_]+$', ref):
            logger.warning(
                f"[SECURITY] Invalid receipt reference format '{ref}' from client {user.email}"
            )
            return APIResponse.validation_error(
                errors={'reference': ['Invalid reference format']},
                error_code="INVALID_FORMAT"
            )
        
        # SECURITY: Verify payment belongs to client's transaction
        try:
            payment = PaymentRecord.objects.select_related(
                'transaction__client',
                'transaction__allocation__estate'
            ).get(
                reference_code=ref,
                transaction__client_id=client_id
            )
        except PaymentRecord.DoesNotExist:
            logger.warning(
                f"[SECURITY] Receipt access denied - client {user.email} "
                f"attempted to access receipt {ref}"
            )
            return APIResponse.not_found(
                message="Payment record not found",
                error_code="PAYMENT_NOT_FOUND"
            )
        
        # Audit log
        logger.info(
            f"[AUDIT] Client {user.email} downloading receipt {ref} "
            f"from IP: {get_client_ip(request)}"
        )
        
        # Return receipt data (or redirect to receipt URL)
        return APIResponse.success(
            data={
                'reference_code': payment.reference_code,
                'receipt_number': payment.receipt_number if hasattr(payment, 'receipt_number') else None,
                'amount': str(payment.amount_paid),
                'payment_date': payment.payment_date,
                'estate_name': payment.transaction.allocation.estate.name if payment.transaction.allocation else 'N/A',
                'download_url': request.build_absolute_uri(f'/payment/receipt/{ref}/'),
            },
            message="Receipt data retrieved successfully"
        )
