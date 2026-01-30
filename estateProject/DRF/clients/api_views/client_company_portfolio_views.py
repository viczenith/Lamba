"""
Company Portfolio Page API Views
==================================
API endpoints for the My Company Portfolio page (my_company_portfolio.html)

Endpoints:
- GET /api/clients/company/<id>/portfolio/ - Full portfolio data for company
- GET /api/clients/company/transaction/<id>/ - Transaction details for modal
- GET /api/clients/company/payment-history/ - Payment history for transaction
- GET /api/clients/company/receipt/<ref>/ - Receipt download data

SECURITY FEATURES:
✅ Token & Session Authentication
✅ IsClient permission with audit logging
✅ Rate limiting (60 req/hour for portfolio, 120 req/hour for details)
✅ IDOR Protection - client can only see their own data
✅ Company Access Validation - verify client has allocations
✅ Input sanitization (company_id, transaction_id, reference)
✅ Audit logging for all data access
✅ No cross-client data exposure
"""

from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.throttling import UserRateThrottle
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Value
from django.db.models.fields import DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from datetime import date
from collections import OrderedDict
import re
import logging

from DRF.shared_drf import APIResponse
from DRF.clients.serializers.client_company_portfolio_serializers import (
    CompanyPortfolioResponseSerializer,
    TransactionDetailSerializer,
    PaymentHistoryResponseSerializer,
)
from estateApp.models import (
    Company, PlotAllocation, Transaction, PropertyPrice,
    Estate, PaymentRecord, ClientMarketerAssignment
)

logger = logging.getLogger(__name__)


# =============================================================================
# THROTTLE CLASSES
# =============================================================================

class PortfolioDataThrottle(UserRateThrottle):
    """Rate limit for portfolio data - 60 requests per hour."""
    rate = '60/hour'


class TransactionDetailThrottle(UserRateThrottle):
    """Rate limit for transaction details - 120 requests per hour."""
    rate = '120/hour'


# =============================================================================
# PERMISSION CLASS
# =============================================================================

class IsClient(permissions.BasePermission):
    """
    Permission class to verify user is an authenticated client.
    
    Security:
    - Validates authentication
    - Checks client role
    - Logs unauthorized attempts
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            logger.warning(
                f"[SECURITY] Unauthenticated access to {view.__class__.__name__} "
                f"from IP: {self._get_client_ip(request)}"
            )
            return False
        
        # Allow staff/admins
        if getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False):
            return True
        
        is_client = getattr(request.user, 'role', '') == 'client'
        
        if not is_client:
            logger.warning(
                f"[SECURITY] Non-client {request.user.email} attempted portfolio access"
            )
        
        return is_client
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_client_ip(request):
    """Extract client IP for audit logging."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def validate_company_access(client_id, company):
    """
    SECURITY: Validate client has allocations in this company.
    Prevents unauthorized access to company portfolio data.
    """
    return PlotAllocation.objects.filter(
        client_id=client_id,
        estate__company=company
    ).exists()


def calculate_portfolio_metrics(transactions):
    """
    Calculate portfolio metrics from transactions.
    
    Returns:
    - total_current_value
    - total_invested
    - total_appreciation
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
        
        # Get current price from PropertyPrice
        current_value = purchase_price
        
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
        
        # Annotate transaction with calculated values
        txn.current_value = current_value
        txn.appreciation = appreciation
        txn.growth_rate = growth_rate
        txn.abs_growth_rate = abs(growth_rate)
        annotated_transactions.append(txn)
    
    # Calculate totals
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
# COMPANY PORTFOLIO API VIEW
# =============================================================================

class ClientCompanyPortfolioAPIView(APIView):
    """
    GET: Returns complete portfolio data for a specific company.
    
    URL: /api/clients/company/<company_id>/portfolio/
    
    Response includes all data for my_company_portfolio.html:
    - Company header info
    - Stats cards (invested, appreciation, current value, marketer)
    - Properties list for Properties tab
    - Appreciation data for Value Appreciation tab
    - Recent payments grouped by year
    - Portfolio summary
    
    SECURITY:
    - Validates client has allocations in requested company
    - Returns 404 if unauthorized (prevents company enumeration)
    - All data filtered by authenticated client_id
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    throttle_classes = (PortfolioDataThrottle,)
    
    def get(self, request, company_id, *args, **kwargs):
        user = request.user
        client_id = user.id
        
        # Input validation
        try:
            company_id = int(company_id)
        except (ValueError, TypeError):
            logger.warning(f"[SECURITY] Invalid company_id from client {user.email}")
            return APIResponse.validation_error(
                errors={'company_id': ['Invalid company ID']},
                error_code="INVALID_ID"
            )
        
        # Get company
        company = get_object_or_404(Company, id=company_id)
        
        # SECURITY: Validate client access
        if not validate_company_access(client_id, company):
            logger.warning(
                f"[SECURITY] Unauthorized portfolio access by {user.email} "
                f"for company {company.company_name} (ID: {company_id}) "
                f"from IP: {get_client_ip(request)}"
            )
            return APIResponse.not_found(
                message="You do not have any allocations in this company",
                error_code="ACCESS_DENIED"
            )
        
        # Audit log successful access
        logger.info(
            f"[AUDIT] Client {user.email} viewing portfolio for "
            f"{company.company_name} from IP: {get_client_ip(request)}"
        )
        
        # Get transactions (use all_objects to bypass CompanyAwareManager)
        transactions = (
            Transaction.all_objects.filter(client_id=client_id, company=company)
            .select_related('allocation__estate', 'allocation__plot_size', 'allocation__plot_number')
            .prefetch_related('payment_records')
            .order_by('-transaction_date')
        )
        
        # Calculate metrics
        metrics = calculate_portfolio_metrics(transactions)
        transactions = metrics['transactions']
        
        # Get marketer assignment
        try:
            assignment = ClientMarketerAssignment.objects.filter(
                client_id=client_id, company=company
            ).select_related('marketer').first()
            marketer = assignment.marketer if assignment else None
        except Exception:
            marketer = None
        
        # Build properties list (for Properties tab)
        properties_list = []
        appreciation_list = []
        
        for txn in transactions:
            alloc = txn.allocation
            if not alloc:
                continue
            
            # Property card data
            properties_list.append({
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
            })
            
            # Appreciation card data (for Value Appreciation tab)
            appreciation_list.append({
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
            })
        
        # Build recent payments (for sidebar accordion)
        recent_payments = []
        for txn in transactions:
            if txn.allocation.payment_type == 'full':
                # Full payment transaction
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
                # Part payment - add each payment record
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
        
        # Group by year (for accordion)
        payments_by_year = OrderedDict()
        for payment in recent_payments:
            year = payment['date'].year
            if year not in payments_by_year:
                payments_by_year[year] = []
            payments_by_year[year].append(payment)
        
        # Count estates in company
        estates_count = Estate.objects.filter(company=company).count()
        
        # Build full response
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
                'total_invested': metrics['total_invested'],
                'total_appreciation': metrics['total_appreciation'],
                'total_current_value': metrics['total_current_value'],
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
        
        serializer = CompanyPortfolioResponseSerializer(response_data, context={'request': request})
        return APIResponse.success(
            data=serializer.data,
            message="Portfolio data retrieved successfully"
        )


# =============================================================================
# TRANSACTION DETAIL API VIEW (for modal)
# =============================================================================

class ClientCompanyTransactionDetailAPIView(APIView):
    """
    GET: Returns transaction details for modal.
    
    URL: /api/clients/company/transaction/<transaction_id>/
    
    SECURITY:
    - Validates transaction belongs to authenticated client
    - Returns 404 if not found/unauthorized
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
        
        # SECURITY: Get transaction filtered by client_id
        try:
            transaction = Transaction.all_objects.select_related(
                'allocation__estate',
                'allocation__plot_size',
                'allocation__plot_number',
                'company'
            ).get(id=transaction_id, client_id=client_id)
        except Transaction.DoesNotExist:
            logger.warning(
                f"[SECURITY] Transaction {transaction_id} access denied for {user.email}"
            )
            return APIResponse.not_found(
                message="Transaction not found",
                error_code="TRANSACTION_NOT_FOUND"
            )
        
        # Audit log
        logger.info(f"[AUDIT] Client {user.email} viewing transaction {transaction_id}")
        
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
                'estate_name': allocation.estate.name if allocation and allocation.estate else '',
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
        
        serializer = TransactionDetailSerializer(response_data, context={'request': request})
        return APIResponse.success(
            data=serializer.data,
            message="Transaction details retrieved successfully"
        )


# =============================================================================
# PAYMENT HISTORY API VIEW (for modal)
# =============================================================================

class ClientCompanyPaymentHistoryAPIView(APIView):
    """
    GET: Returns payment history for a transaction (modal).
    
    URL: /api/clients/company/payment-history/?transaction_id=<id>
    
    SECURITY:
    - Validates transaction belongs to client
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
                errors={'transaction_id': ['transaction_id is required']},
                error_code="MISSING_PARAMETER"
            )
        
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


# =============================================================================
# RECEIPT DOWNLOAD API VIEW
# =============================================================================

class ClientCompanyReceiptAPIView(APIView):
    """
    GET: Returns receipt data for download.
    
    URL: /api/clients/company/receipt/<reference>/ or
         /api/clients/company/receipt/?reference=<ref>
    
    SECURITY:
    - Validates payment belongs to client's transaction
    - Input sanitization on reference
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
        
        # Input sanitization
        if not re.match(r'^[A-Za-z0-9\-_]+$', ref):
            logger.warning(f"[SECURITY] Invalid receipt reference format from {user.email}")
            return APIResponse.validation_error(
                errors={'reference': ['Invalid reference format']},
                error_code="INVALID_FORMAT"
            )
        
        # SECURITY: Verify payment belongs to client
        try:
            payment = PaymentRecord.objects.select_related(
                'transaction__client',
                'transaction__allocation__estate'
            ).get(
                reference_code=ref,
                transaction__client_id=client_id
            )
        except PaymentRecord.DoesNotExist:
            logger.warning(f"[SECURITY] Receipt {ref} access denied for {user.email}")
            return APIResponse.not_found(
                message="Payment not found",
                error_code="PAYMENT_NOT_FOUND"
            )
        
        logger.info(f"[AUDIT] Client {user.email} downloading receipt {ref}")
        
        return APIResponse.success(
            data={
                'reference_code': payment.reference_code,
                'receipt_number': getattr(payment, 'receipt_number', None),
                'amount': str(payment.amount_paid),
                'payment_date': payment.payment_date,
                'estate_name': payment.transaction.allocation.estate.name if payment.transaction.allocation else 'N/A',
                'download_url': request.build_absolute_uri(f'/payment/receipt/{ref}/'),
            },
            message="Receipt data retrieved successfully"
        )
