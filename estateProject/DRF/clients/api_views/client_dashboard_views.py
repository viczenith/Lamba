"""
Client Dashboard API Views
==========================
DRF views for the client dashboard page (client_side.html)

This module provides secure API endpoints for:
- Dashboard statistics (properties, payments, allocations)
- Active promotional offers by company
- Price history/increments by company
- Estate listings for the client
- Promotion details

SECURITY IMPLEMENTATIONS:
1. Authentication required (Token/Session)
2. Rate limiting (throttling) to prevent abuse
3. Company-scoped data isolation
4. Input validation and sanitization
5. Audit logging for access tracking
6. Error handling without information disclosure
7. Query parameter validation
8. XSS prevention via HTML escaping

Author: System
Version: 2.0
Last Updated: December 2024
"""

from rest_framework import permissions, status
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response

from DRF.shared_drf import APIResponse
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import UserRateThrottle
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.utils.html import escape
from django.db.models import Prefetch, Q, Count
import logging

from estateApp.models import (
    Transaction, PlotAllocation, PlotSizeUnits, PropertyPrice, PriceHistory,
    PromotionalOffer, Estate, PlotSize, PlotNumber, Company
)

from DRF.clients.serializers.client_dashboard_serializers import (
    EstateDetailSerializer, PromotionDashboardSerializer, PriceHistoryListSerializer,
    EstateSizePriceSerializer, PromotionDetailSerializer, PromotionListItemSerializer, 
    PromotionalOfferSimpleSerializer, CompanyDashboardSerializer
)

logger = logging.getLogger(__name__)


# =============================================================================
# THROTTLE CLASSES
# =============================================================================

class ClientDashboardThrottle(UserRateThrottle):
    """
    Standard rate limiting for dashboard API.
    60 requests per minute per user.
    """
    rate = '60/minute'
    scope = 'client_dashboard'


class ClientDashboardBurstThrottle(UserRateThrottle):
    """
    Burst rate limiting to prevent rapid-fire requests.
    10 requests per second per user.
    """
    rate = '10/second'
    scope = 'client_dashboard_burst'


class PromotionDetailThrottle(UserRateThrottle):
    """
    Rate limiting for promotion detail requests.
    30 requests per minute per user.
    """
    rate = '30/minute'
    scope = 'promotion_detail'


# =============================================================================
# SECURITY UTILITY FUNCTIONS
# =============================================================================

def log_access(user, action, resource_type, resource_id=None, company_id=None, success=True, details=None):
    """
    Log access attempts for security auditing.
    SECURITY: Track all data access for compliance/forensics.
    """
    log_data = {
        'user_id': user.id if user else None,
        'user_email': getattr(user, 'email', 'anonymous'),
        'action': action,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'company_id': company_id,
        'success': success,
        'details': details,
        'timestamp': timezone.now().isoformat()
    }
    
    if success:
        logger.info(f"ACCESS: {action} on {resource_type}", extra=log_data)
    else:
        logger.warning(f"ACCESS_DENIED: {action} on {resource_type}", extra=log_data)


def validate_integer_param(value, param_name, min_val=1, max_val=999999999):
    """
    Validate integer parameters to prevent injection attacks.
    SECURITY: Strict validation of user inputs.
    """
    if value is None:
        return None
    
    try:
        int_val = int(value)
        if int_val < min_val or int_val > max_val:
            logger.warning(f"SECURITY: Invalid {param_name} value: {value}")
            return None
        return int_val
    except (ValueError, TypeError):
        logger.warning(f"SECURITY: Non-integer {param_name}: {value}")
        return None


def sanitize_string(value):
    """
    Sanitize string to prevent XSS attacks.
    SECURITY: Always escape HTML in user-facing data.
    """
    if value is None:
        return None
    return escape(str(value))


def _get_active_promo_for_estate(estate):
    """
    Get the currently active promotional offer for an estate.
    SECURITY: Returns highest discount promo that's currently valid.
    """
    try:
        today = timezone.localdate()
        return PromotionalOffer.objects.filter(
            estates=estate, 
            start__lte=today, 
            end__gte=today
        ).order_by('-discount').first()
    except Exception as e:
        logger.warning(f"Error getting active promo for estate {estate.id}: {e}")
        return None


def get_user_affiliated_companies(user):
    """
    Get all companies a user is affiliated with.
    SECURITY: Centralizes company access logic.
    """
    companies = set()
    
    # Check direct company affiliation
    if hasattr(user, 'company_profile') and user.company_profile:
        companies.add(user.company_profile)
    
    # Check CompanyClientProfile for multi-company clients
    try:
        from estateApp.models import CompanyClientProfile
        client_profiles = CompanyClientProfile.objects.filter(user=user).values_list('company', flat=True)
        companies.update(client_profiles)
    except Exception as e:
        logger.warning(f"Error getting client companies for user {user.id}: {e}")
    
    return list(companies)


class ClientDashboardAPIView(APIView):
    """
    Comprehensive client dashboard endpoint with company tenancy support.
    
    Returns:
    - User's affiliated companies
    - Per-company statistics (properties, payments status)
    - Per-company active promotions
    - Per-company price history
    
    SECURITY IMPLEMENTATIONS:
    - Token/Session authentication
    - Rate limiting throttles
    - Company-scoped data isolation
    - XSS prevention via HTML escaping
    - Audit logging
    - Error handling without information disclosure
    
    Supports single or multiple company affiliations for clients.
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = [ClientDashboardThrottle, ClientDashboardBurstThrottle]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            
            # Get all companies affiliated with this user
            affiliated_companies = get_user_affiliated_companies(user)
            
            # Log access attempt
            log_access(user, 'dashboard_view', 'dashboard', 
                      company_id=affiliated_companies[0].id if affiliated_companies else None)
            
            # If no company affiliation, return empty response with template-compatible format
            if not affiliated_companies:
                payload = {
                    "user": {
                        "id": user.id,
                        "full_name": sanitize_string(getattr(user, 'full_name', '')),
                        "email": sanitize_string(user.email),
                    },
                    # Stats cards section - TEMPLATE FORMAT
                }
                return Response(payload, status=status.HTTP_200_OK)
            
            # Aggregate stats across all companies
            total_properties_all = 0
            fully_paid_and_allocated_all = 0
            not_fully_paid_all = 0
            paid_complete_not_allocated_all = 0
            
            # Collect all active promotions across companies
            today = timezone.localdate()
            all_active_promos = []
            
            # Collect price updates organized by company
            company_price_updates = {}
            
            for company in affiliated_companies:
                # Company-specific stats
                tx_qs = Transaction.objects.filter(
                    client=user,
                    allocation__estate__company=company
                ).select_related('allocation__estate', 'allocation__plot_size_unit')
                
                total_properties = tx_qs.count()
                fully_paid_and_allocated = 0
                paid_complete_not_allocated = 0
                not_fully_paid = 0
                
                for t in tx_qs:
                    try:
                        allocation = getattr(t, 'allocation', None)
                        if not allocation:
                            not_fully_paid += 1
                            continue
                        
                        payment_type = getattr(allocation, 'payment_type', '')
                        status_val = getattr(t, 'status', None)
                        
                        # Fully paid AND allocated (has plot number)
                        if payment_type == 'full' or (status_val and str(status_val).lower() in ('fully paid', 'paid complete', 'paid_complete')):
                            plot_number = getattr(allocation, 'plot_number', None)
                            if plot_number:
                                fully_paid_and_allocated += 1
                            else:
                                paid_complete_not_allocated += 1
                        else:
                            not_fully_paid += 1
                    except Exception:
                        not_fully_paid += 1
                        continue
                
                # Aggregate
                total_properties_all += total_properties
                fully_paid_and_allocated_all += fully_paid_and_allocated
                not_fully_paid_all += not_fully_paid
                paid_complete_not_allocated_all += paid_complete_not_allocated
                
                # Company-specific active promotions
                active_promos_qs = PromotionalOffer.objects.filter(
                    estates__company=company,
                    start__lte=today,
                    end__gte=today
                ).distinct().prefetch_related(
                    Prefetch('estates', queryset=Estate.objects.filter(company=company).prefetch_related(
                        'property_prices__plot_unit__plot_size'
                    ))
                ).order_by('-discount')[:10]  # SECURITY: Limit results
                
                active_promos_data = PromotionDashboardSerializer(
                    active_promos_qs,
                    many=True,
                    context={'request': request}
                ).data
                all_active_promos.extend(active_promos_data)
                
                # Company-specific price history organized for accordion
                latest_histories = PriceHistory.objects.filter(
                    price__estate__company=company
                ).select_related(
                    'price', 'price__estate', 'price__plot_unit', 'price__plot_unit__plot_size'
                ).order_by('-recorded_at')[:50]  # SECURITY: Limit results
                
                latest_value_data = PriceHistoryListSerializer(latest_histories, many=True).data
                
                # Check for new updates (recorded in last 7 days)
                seven_days_ago = timezone.now() - timedelta(days=7)
                has_new = any(h['recorded_at'] > seven_days_ago.isoformat() for h in latest_value_data)
                
                # Add is_new flag to updates
                for update in latest_value_data:
                    update['is_new'] = update['recorded_at'] > seven_days_ago.isoformat()
                
                # Organize by company - SECURITY: Sanitize company name
                company_name = sanitize_string(
                    company.company_name if hasattr(company, 'company_name') else str(company)
                )
                company_price_updates[company.id] = {
                    "company_name": company_name,
                    "company_id": company.id,
                    # Ensure we return a serializable URL or None for file fields
                    "company_logo": (getattr(company, 'logo').url if getattr(company, 'logo', None) and hasattr(getattr(company, 'logo'), 'url') else None),
                    "updates": latest_value_data,
                    "has_new": has_new,
                }
            
            # Build final response with TEMPLATE-COMPATIBLE FORMAT
            payload = {
                "user": {
                    "id": user.id,
                    "full_name": sanitize_string(getattr(user, 'full_name', '')),
                    "email": sanitize_string(user.email),
                },
                # ===== STATS CARDS SECTION =====
                "total_properties": total_properties_all,
                "fully_paid_and_allocated": fully_paid_and_allocated_all,
                "not_fully_paid": not_fully_paid_all,
                "paid_complete_not_allocated": paid_complete_not_allocated_all,
                
                # ===== ACTIVE PROMOTIONS SECTION =====
                "active_promotions": all_active_promos,
                
                # ===== PRICE INCREMENTS SECTION (organized by company) =====
                "latest_value_by_company": list(company_price_updates.values()),
            }
            return Response(payload, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Dashboard API error for user {request.user.id}: {e}")
            return APIResponse.server_error(
                message="Failed to load dashboard data",
                error_code="DASHBOARD_ERROR"
            )


class PriceUpdateDetailAPIView(RetrieveAPIView):
    """
    Retrieve detailed price update with company tenancy check.
    
    SECURITY IMPLEMENTATIONS:
    - Company-scoped data isolation
    - Rate limiting
    - Audit logging
    - Input validation
    """
    queryset = PriceHistory.objects.select_related('price', 'price__estate', 'price__plot_unit', 'price__plot_unit__plot_size')
    serializer_class = PriceHistoryListSerializer
    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = [ClientDashboardThrottle]
    lookup_field = 'pk'
    
    def get_queryset(self):
        """Filter to only price histories for user's affiliated companies."""
        user = self.request.user
        affiliated_companies = get_user_affiliated_companies(user)
        return super().get_queryset().filter(price__estate__company__in=affiliated_companies)
    
    def retrieve(self, request, *args, **kwargs):
        """Override to add security logging."""
        try:
            pk = validate_integer_param(kwargs.get('pk'), 'pk')
            if pk is None:
                return APIResponse.validation_error(
                    errors={'pk': ['Invalid price update ID']},
                    error_code="INVALID_ID"
                )
            
            instance = self.get_object()
            log_access(request.user, 'price_update_detail', 'price_history', pk,
                      company_id=instance.price.estate.company_id)
            
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Price update detail error: {e}")
            return APIResponse.not_found(
                message="Price update not found or access denied",
                error_code="PRICE_UPDATE_NOT_FOUND"
            )


class EstateListAPIView(ListAPIView):
    """
    API endpoint for estate list with promotional offer support and company isolation.
    
    Endpoints:
    1. GET /api/estates/ - Returns paginated list of estates for user's affiliated companies
    2. GET /api/estates/?estate_id=X - Returns single estate detail (if user has access via company)
    3. GET /api/estates/?q=search - Filter estates by name/location (company-scoped)
    
    SECURITY IMPLEMENTATIONS:
    - Company-scoped data isolation
    - Rate limiting
    - Input validation
    - XSS prevention
    - Audit logging
    
    Response respects company tenancy - only returns estates from user's affiliated companies.
    """
    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = [ClientDashboardThrottle]
    pagination_class = PageNumberPagination
    serializer_class = None

    def _get_user_companies(self, request):
        """Get all companies affiliated with the current user."""
        return get_user_affiliated_companies(request.user)

    def get_queryset(self):
        companies = self._get_user_companies(self.request)
        qs = Estate.objects.filter(company__in=companies).order_by('-date_added').prefetch_related(
            Prefetch(
                'promotional_offers',
                queryset=PromotionalOffer.objects.order_by('-discount', '-start')
            ),
            Prefetch(
                'property_prices',
                queryset=PropertyPrice.objects.select_related('plot_unit__plot_size').order_by('-created_at')
            )
        )
        
        # SECURITY: Validate and sanitize search parameter
        q = self.request.GET.get('q', '').strip()
        if q:
            # Limit search query length
            q = q[:100]
            qs = qs.filter(Q(name__icontains=q) | Q(location__icontains=q))
        return qs

    def list(self, request, *args, **kwargs):
        try:
            estate_id = request.GET.get('estate_id')
            companies = self._get_user_companies(request)

            # Single estate detail endpoint
            if estate_id:
                # SECURITY: Validate estate_id
                estate_id = validate_integer_param(estate_id, 'estate_id')
                if estate_id is None:
                    return APIResponse.validation_error(
                        errors={'estate_id': ['Invalid estate ID']},
                        error_code="INVALID_ID"
                    )
                
                try:
                    estate = Estate.objects.filter(
                        pk=estate_id,
                        company__in=companies
                    ).prefetch_related(
                        'property_prices__plot_unit__plot_size',
                        Prefetch(
                            'promotional_offers',
                            queryset=PromotionalOffer.objects.order_by('-discount', '-start')
                        )
                    ).get()
                except (Estate.DoesNotExist, ValueError):
                    log_access(request.user, 'estate_detail', 'estate', estate_id, success=False)
                    return APIResponse.not_found(
                        message="Estate not found or access denied",
                        error_code="ESTATE_NOT_FOUND"
                    )

                log_access(request.user, 'estate_detail', 'estate', estate_id, 
                          company_id=estate.company_id)
                serializer = EstateDetailSerializer(estate, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)

            # List all estates for user's companies
            log_access(request.user, 'estate_list', 'estates')
            qs = self.get_queryset()
            page = self.paginate_queryset(qs)
            
            if page is not None:
                data = []
                for e in page:
                    promos_qs = e.promotional_offers.all()
                    promo_preview = [
                        PromotionalOfferSimpleSerializer(p, context={'request': request}).data
                        for p in promos_qs
                    ]
                    
                    date_added = getattr(e, 'date_added', None)
                    created_at_str = None
                    if date_added:
                        if hasattr(date_added, 'isoformat'):
                            created_at_str = date_added.isoformat()
                        elif hasattr(date_added, 'strftime'):
                            created_at_str = date_added.strftime('%Y-%m-%d')
                        else:
                            created_at_str = str(date_added)
                    
                    # SECURITY: Sanitize string fields
                    estate_data = {
                        "id": e.id,
                        "name": sanitize_string(e.name),
                        "location": sanitize_string(e.location),
                        "created_at": created_at_str,
                        "company": {
                            "id": e.company.id,
                            "name": sanitize_string(
                                e.company.company_name if hasattr(e.company, 'company_name') else str(e.company)
                            ),
                            # Include company logo (may be relative/storage path); UI prefers absolute URL when available
                            "company_logo": (getattr(e.company, 'logo').url if getattr(e.company, 'logo', None) and hasattr(getattr(e.company, 'logo'), 'url') else None)
                        },
                        "promos_count": len(promo_preview),
                        "promotional_offers": promo_preview,
                    }
                    
                    data.append(estate_data)
                return self.get_paginated_response(data)

            # Fallback (no pagination)
            data = []
            for e in qs[:100]:  # SECURITY: Limit unpaginated results
                promos_qs = e.promotional_offers.all()
                promo_preview = [
                    PromotionalOfferSimpleSerializer(p, context={'request': request}).data
                    for p in promos_qs
                ]
                
                date_added = getattr(e, 'date_added', None)
                created_at_str = None
                if date_added:
                    if hasattr(date_added, 'isoformat'):
                        created_at_str = date_added.isoformat()
                    elif hasattr(date_added, 'strftime'):
                        created_at_str = date_added.strftime('%Y-%m-%d')
                    else:
                        created_at_str = str(date_added)
                
                # SECURITY: Sanitize string fields
                data.append({
                    "id": e.id,
                    "name": sanitize_string(e.name),
                    "location": sanitize_string(e.location),
                    "created_at": created_at_str,
                    "company": {
                        "id": e.company.id,
                        "name": sanitize_string(
                            e.company.company_name if hasattr(e.company, 'company_name') else str(e.company)
                        ),
                    },
                    "promos_count": len(promo_preview),
                    "promotional_offers": promo_preview,
                })
            return Response({'results': data, 'count': len(data), 'next': None, 'previous': None}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Estate list error: {e}")
            return APIResponse.server_error(
                message="Failed to retrieve estates",
                error_code="ESTATE_LIST_ERROR"
            )


class ActivePromotionsListAPIView(APIView):
    """
    Get active promotional offers for user's affiliated companies only.
    
    SECURITY IMPLEMENTATIONS:
    - Company-scoped data isolation
    - Rate limiting
    - Audit logging
    """
    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = [ClientDashboardThrottle]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            companies = get_user_affiliated_companies(user)
            
            log_access(user, 'active_promotions_list', 'promotions')
            
            today = timezone.localdate()
            promos = PromotionalOffer.objects.filter(
                estates__company__in=companies,
                start__lte=today,
                end__gte=today
            ).distinct().prefetch_related(
                Prefetch('estates', queryset=Estate.objects.prefetch_related('property_prices__plot_unit__plot_size'))
            ).order_by('-discount')[:50]  # SECURITY: Limit results
            
            serializer = PromotionDashboardSerializer(promos, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Active promotions list error: {e}")
            return APIResponse.server_error(
                message="Failed to retrieve promotions",
                error_code="PROMOTIONS_ERROR"
            )


class SmallPageNumberPagination(PageNumberPagination):
    """Pagination for promotion lists with sensible limits."""
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50


class PromotionsListAPIView(APIView):
    """
    Get all promotions (active, past, upcoming) for user's affiliated companies.
    
    SECURITY IMPLEMENTATIONS:
    - Company-scoped data isolation
    - Rate limiting
    - Input validation (filter, search params)
    - Result limiting
    - Audit logging
    """
    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = [ClientDashboardThrottle]
    pagination_class = SmallPageNumberPagination

    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            companies = get_user_affiliated_companies(user)
            
            log_access(user, 'promotions_list', 'promotions')
            
            today = timezone.localdate()
            
            # SECURITY: Validate and sanitize search parameter
            q = request.GET.get('q', '').strip()[:100]  # Limit search length
            
            # SECURITY: Validate filter parameter
            filt = request.GET.get('filter', 'all').lower()
            if filt not in ('all', 'active', 'past'):
                filt = 'all'

            base_qs = PromotionalOffer.objects.filter(
                estates__company__in=companies
            ).distinct().prefetch_related(
                Prefetch('estates', queryset=Estate.objects.only('id', 'name', 'location'))
            ).order_by('-start', '-created_at')

            active_qs = base_qs.filter(start__lte=today, end__gte=today)
            active_serialized = PromotionListItemSerializer(
                active_qs[:20],  # SECURITY: Limit active results
                many=True, 
                context={'request': request}
            ).data

            if filt == 'active':
                promos_qs = active_qs
            elif filt == 'past':
                promos_qs = base_qs.filter(end__lt=today)
            else:
                promos_qs = base_qs.exclude(pk__in=active_qs.values_list('pk', flat=True))

            if q:
                promos_qs = promos_qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(promos_qs, request, view=self)
            serialized_page = PromotionListItemSerializer(page, many=True, context={'request': request}).data
            paginated_response = paginator.get_paginated_response(serialized_page).data

            return Response({
                "active_promotions": active_serialized,
                "promotions": paginated_response
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Promotions list error: {e}")
            return APIResponse.server_error(
                message="Failed to retrieve promotions",
                error_code="PROMOTIONS_ERROR"
            )


class PromotionDetailAPIView(RetrieveAPIView):
    """
    Get detailed promotion with company access control.
    
    SECURITY IMPLEMENTATIONS:
    - Company-scoped data isolation
    - Stricter rate limiting
    - Input validation
    - Audit logging
    """
    queryset = PromotionalOffer.objects.prefetch_related(
        Prefetch('estates', queryset=Estate.objects.prefetch_related('property_prices__plot_unit__plot_size'))
    )
    serializer_class = PromotionDetailSerializer
    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = [PromotionDetailThrottle]
    lookup_field = 'pk'
    
    def get_queryset(self):
        """Filter promotions to only those for user's affiliated companies."""
        user = self.request.user
        companies = get_user_affiliated_companies(user)
        return super().get_queryset().filter(estates__company__in=companies).distinct()
    
    def retrieve(self, request, *args, **kwargs):
        """Override to add security validation and logging."""
        try:
            pk = validate_integer_param(kwargs.get('pk'), 'pk')
            if pk is None:
                return APIResponse.validation_error(
                    errors={'pk': ['Invalid promotion ID']},
                    error_code="INVALID_ID"
                )
            
            try:
                instance = self.get_object()
            except Exception:
                log_access(request.user, 'promotion_detail', 'promotion', pk, success=False)
                return APIResponse.not_found(
                    message="Promotion not found or access denied",
                    error_code="PROMOTION_NOT_FOUND"
                )
            
            log_access(request.user, 'promotion_detail', 'promotion', pk)
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Promotion detail error: {e}")
            return APIResponse.server_error(
                message="Failed to retrieve promotion",
                error_code="PROMOTION_ERROR"
            )

