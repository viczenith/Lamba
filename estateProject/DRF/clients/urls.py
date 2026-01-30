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
from DRF.clients.api_views.client_chat_views import (
    ClientChatListAPIView,
    ClientChatDetailAPIView,
    ClientChatSendAPIView,
    ClientChatDeleteAPIView,
    ClientChatDeleteForEveryoneAPIView,
    ClientChatUnreadCountAPIView,
    ClientChatMarkAsReadAPIView,
    ClientChatPollAPIView,
    ClientChatCompaniesAPIView,
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

# ============================================================================
# CLIENT CHAT ENDPOINTS
# ============================================================================

urlpatterns += [
    path('api/clients/chat/companies/', ClientChatCompaniesAPIView.as_view(), name='api-client-chat-companies'),
    path('api/clients/chat/', ClientChatListAPIView.as_view(), name='api-client-chat-list'),
    path('api/clients/chat/send/', ClientChatSendAPIView.as_view(), name='api-client-chat-send'),
    path('api/clients/chat/<int:pk>/', ClientChatDetailAPIView.as_view(), name='api-client-chat-detail'),
    path('api/clients/chat/<int:pk>/delete/', ClientChatDeleteAPIView.as_view(), name='api-client-chat-delete'),
    path('api/clients/chat/delete-for-everyone/', ClientChatDeleteForEveryoneAPIView.as_view(), name='api-client-chat-delete-for-everyone'),
    path('api/clients/chat/unread-count/', ClientChatUnreadCountAPIView.as_view(), name='api-client-chat-unread-count'),
    path('api/clients/chat/mark-as-read/', ClientChatMarkAsReadAPIView.as_view(), name='api-client-chat-mark-as-read'),
    path('api/clients/chat/poll/', ClientChatPollAPIView.as_view(), name='api-client-chat-poll'),
]
