"""
Client API URLs
================
URL patterns for client-facing DRF API endpoints.

All endpoints require authentication and client role verification.
"""

from django.urls import path

# Import from the correct api_views location
from DRF.clients.api_views.client_estate_detail_views import (
    ClientEstateDetailAPIView,
    SecurePrototypeImageAPIView,
    SecureEstateLayoutAPIView,
    SecureFloorPlanAPIView,
    ClientEstateAccessCheckAPIView,
)

urlpatterns = [
    # ==========================================================================
    # CLIENT ESTATE DETAIL ENDPOINTS
    # ==========================================================================
    
    # Main estate detail endpoint
    # GET: Retrieve full estate details for a specific plot size
    path(
        'api/client/estate/<int:estate_id>/plot-size/<int:plot_size_id>/',
        ClientEstateDetailAPIView.as_view(),
        name='api-client-estate-detail'
    ),
    
    # Access check endpoint (utility for pre-flight checks)
    # GET: Check if client has access to an estate
    path(
        'api/client/estate/<int:estate_id>/access-check/',
        ClientEstateAccessCheckAPIView.as_view(),
        name='api-client-estate-access-check'
    ),
    
    # ==========================================================================
    # SECURE MEDIA ENDPOINTS
    # ==========================================================================
    
    # Prototype images (authenticated access only)
    path(
        'api/secure/prototype/<int:prototype_id>/image/',
        SecurePrototypeImageAPIView.as_view(),
        name='api-secure-prototype-image'
    ),
    
    # Estate layout images (authenticated access only)
    path(
        'api/secure/estate-layout/<int:layout_id>/image/',
        SecureEstateLayoutAPIView.as_view(),
        name='api-secure-estate-layout'
    ),
    
    # Floor plan images (authenticated access only)
    path(
        'api/secure/floor-plan/<int:plan_id>/image/',
        SecureFloorPlanAPIView.as_view(),
        name='api-secure-floor-plan'
    ),
]
