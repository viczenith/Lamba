"""
DRF API Routes - Consolidated endpoints for multi-tenant architecture.
Includes all authentication, property management, and subscription endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from DRF.shared_drf.auth_urls import urlpatterns as shared_auth_urlpatterns

# Import ViewSets - Phase 3 Endpoints (Admin module)
from DRF.admin.api_views.auth_views import (
    AuthenticationViewSet, CompanyViewSet, UserManagementViewSet
)
from DRF.admin.api_views.property_views import (
    EstateViewSet, PropertyViewSet, PropertyAllocationViewSet
)
from DRF.admin.api_views.subscription_views import (
    SubscriptionViewSet, PaymentViewSet, TransactionViewSet
)

# Import existing client/marketer views
from DRF.clients.api_views.client_dashboard_views import ActivePromotionsListAPIView, ClientDashboardAPIView, EstateListAPIView, PriceUpdateDetailAPIView, PromotionDetailAPIView, PromotionsListAPIView
from DRF.clients.api_views.client_estate_detail_views import ClientEstateDetailAPIView, SecurePrototypeImageAPIView, SecureEstateLayoutAPIView, SecureFloorPlanAPIView, ClientEstateAccessCheckAPIView

from DRF.clients.api_views.client_profile_views import (
    # Overview Tab
    ClientProfileOverviewView,
    ClientProfileView,
    # Edit Profile Tab  
    ClientProfileEditView,
    ClientProfileUpdateView,
    ClientProfileImageUploadView,
    # Password Tab
    ClientChangePasswordView,
    ChangePasswordView,
)
# My Companies Page (separate file)
from DRF.clients.api_views.client_my_companies_views import (
    ClientMyCompaniesAPIView,
)
# My Company Portfolio Page (separate file)
from DRF.clients.api_views.client_company_portfolio_views import (
    ClientCompanyPortfolioAPIView,
    ClientCompanyTransactionDetailAPIView,
    ClientCompanyPaymentHistoryAPIView,
    ClientCompanyReceiptAPIView,
)
# Notification List Page (notification.html)
from DRF.clients.api_views.client_notification_list_views import (
    ClientNotificationListPageAPIView,
    ClientNotificationListAPI,
    ClientUnreadCountAPIView,
    ClientMarkReadAPIView,
    ClientMarkUnreadAPIView,
    ClientMarkAllReadAPIView,
)
# Notification Detail Page (notification_detail.html)
from DRF.clients.api_views.client_notification_detail_views import (
    ClientNotificationDetailPageAPIView,
    ClientNotificationDetailAPI,
    ClientNotificationDeleteAPIView,
)
from DRF.marketers.api_views.marketer_notification_views import (
    MarketerMarkAllReadAPI,
    MarketerMarkReadAPI,
    MarketerMarkUnreadAPI,
    MarketerNotificationDetailAPI,
    MarketerNotificationListAPI,
    MarketerUnreadCountAPI,
)
from DRF.marketers.api_views.marketer_chat_views import (
    MarketerChatDeleteAPIView,
    MarketerChatDeleteForEveryoneAPIView,
    MarketerChatDetailAPIView,
    MarketerChatListAPIView,
    MarketerChatMarkAsReadAPIView,
    MarketerChatPollAPIView,
    MarketerChatSendAPIView,
    MarketerChatUnreadCountAPIView,
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
)
from DRF.marketers.api_views.client_record_views import MarketerClientDetailAPIView, MarketerClientListAPIView
from DRF.marketers.api_views.marketer_dashboard_views import MarketerChartRangeAPIView, MarketerDashboardAPIView
from DRF.marketers.api_views.marketer_profile_views import (
    MarketerChangePasswordView,
    MarketerProfileUpdateView,
    MarketerProfileView,
    MarketerTransactionsView,
)
from DRF.shared_drf.shared_header_views import (
    AdminClientChatListAPIView,
    AdminMarketerChatListAPIView,
    ChatUnreadCountAPIView,
    HeaderDataAPIView,
    MarkNotificationReadAPIView,
    NotificationsListAPIView,
)
from DRF.admin_support.api_views.chat_views import (
    SupportChatDeleteMessageAPIView,
    SupportChatMarkReadAPIView,
    SupportChatPollAPIView,
    SupportChatThreadAPIView,
)
from DRF.clients.api_views.device_token_views import DeviceTokenListView, DeviceTokenRegisterView

# Create router
router = DefaultRouter()

# ============================================================================
# PHASE 3 ENDPOINTS - NEW DRF ENDPOINTS WITH FULL SECURITY
# ============================================================================

# Authentication
router.register(r'auth', AuthenticationViewSet, basename='auth')

# Company Management
router.register(r'companies', CompanyViewSet, basename='company')

# User Management
router.register(r'users', UserManagementViewSet, basename='user')

# Property Management
router.register(r'estates', EstateViewSet, basename='estate')
router.register(r'properties', PropertyViewSet, basename='property')
router.register(r'allocations', PropertyAllocationViewSet, basename='allocation')

# Subscription & Payments
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'transactions', TransactionViewSet, basename='transaction')

app_name = 'drf'

urlpatterns = [
    # Include all router URLs
    path('', include(router.urls)),

    # Unified token auth (supports multi-role selection)
    path('', include(shared_auth_urlpatterns)),
    
    # SHARED HEADER
    path('header-data/', HeaderDataAPIView.as_view(), name='api-header-data'),
    path('chat-unread-count/', ChatUnreadCountAPIView.as_view(), name='chat_unread_count'),
    path('notifications/', NotificationsListAPIView.as_view(), name='api-notifications-list'),
    path('notifications/mark-read/<int:pk>/', MarkNotificationReadAPIView.as_view(), name='mark_notification_read_api'),
    path('admin/clients/unread/', AdminClientChatListAPIView.as_view(), name='admin_client_chat_list_api'),
    path('admin/marketers/unread/', AdminMarketerChatListAPIView.as_view(), name='admin_marketer_chat_list_api'),
    
    path('admin-support/chat/<str:role>/<int:participant_id>/', SupportChatThreadAPIView.as_view(), name='support_chat_thread_api'),
    path('admin-support/chat/<str:role>/<int:participant_id>/poll/', SupportChatPollAPIView.as_view(), name='support_chat_poll_api'),
    path('admin-support/chat/<str:role>/<int:participant_id>/mark-read/', SupportChatMarkReadAPIView.as_view(), name='support_chat_mark_read_api'),
    path('admin-support/chat/messages/<int:pk>/delete/', SupportChatDeleteMessageAPIView.as_view(), name='support_chat_delete_message_api'),


    # client dashboard
    path('client/dashboard-data/', ClientDashboardAPIView.as_view(), name='client-dashboard-data'),
    path('api/price-update/<int:pk>/', PriceUpdateDetailAPIView.as_view(), name='api-price-update'),
    path('estates/', EstateListAPIView.as_view(), name='estates-list'),
    path('promotions/active/', ActivePromotionsListAPIView.as_view(), name='active-promotions-list'),
    path('promotions/', PromotionsListAPIView.as_view(), name='promotions-list'),
    path('promotions/<int:pk>/', PromotionDetailAPIView.as_view(), name='promotion-detail'),

    # =========================================================================
    # CLIENT PROFILE ENDPOINTS
    # =========================================================================
    
    # Overview Tab
    path('clients/profile/', ClientProfileView.as_view(), name='client-profile'),
    path('clients/profile/overview/', ClientProfileOverviewView.as_view(), name='client-profile-overview'),
    
    # Edit Profile Tab
    path('clients/profile/update/', ClientProfileUpdateView.as_view(), name='client-profile-update'),
    path('clients/profile/edit/', ClientProfileEditView.as_view(), name='client-profile-edit'),
    path('clients/profile/image/', ClientProfileImageUploadView.as_view(), name='client-profile-image'),
    
    # Password Tab
    path('clients/change-password/', ChangePasswordView.as_view(), name='client-change-password'),
    path('clients/password/change/', ClientChangePasswordView.as_view(), name='client-password-change'),

    # =========================================================================
    # MY COMPANIES PAGE ENDPOINTS
    # =========================================================================
    path('clients/my-companies/', ClientMyCompaniesAPIView.as_view(), name='client-my-companies'),

    # =========================================================================
    # MY COMPANY PORTFOLIO PAGE ENDPOINTS
    # =========================================================================
    path('clients/company/<int:company_id>/portfolio/', ClientCompanyPortfolioAPIView.as_view(), name='client-company-portfolio'),
    path('clients/company/transaction/<int:transaction_id>/', ClientCompanyTransactionDetailAPIView.as_view(), name='client-company-transaction-detail'),
    path('clients/company/payment-history/', ClientCompanyPaymentHistoryAPIView.as_view(), name='client-company-payment-history'),
    path('clients/company/receipt/<str:reference>/', ClientCompanyReceiptAPIView.as_view(), name='client-company-receipt'),
    path('clients/company/receipt/', ClientCompanyReceiptAPIView.as_view(), name='client-company-receipt-query'),

    # =========================================================================
    # NOTIFICATION LIST PAGE ENDPOINTS (notification.html)
    # =========================================================================
    path('clients/notifications/page/', ClientNotificationListPageAPIView.as_view(), name='client-notifications-page'),
    path('client/notifications/', ClientNotificationListAPI.as_view(), name='notifications-list'),
    path('client/notifications/unread-count/', ClientUnreadCountAPIView.as_view(), name='notifications-unread-count'),
    path('client/notifications/<int:pk>/mark-read/', ClientMarkReadAPIView.as_view(), name='notifications-mark-read'),
    path('client/notifications/<int:pk>/mark-unread/', ClientMarkUnreadAPIView.as_view(), name='notifications-mark-unread'),
    path('client/notifications/mark-all-read/', ClientMarkAllReadAPIView.as_view(), name='notifications-mark-all-read'),

    # =========================================================================
    # NOTIFICATION DETAIL PAGE ENDPOINTS (notification_detail.html)
    # =========================================================================
    path('clients/notifications/<int:pk>/detail/', ClientNotificationDetailPageAPIView.as_view(), name='client-notification-detail-page'),
    path('client/notifications/<int:pk>/', ClientNotificationDetailAPI.as_view(), name='notifications-detail'),
    path('clients/notifications/<int:pk>/delete/', ClientNotificationDeleteAPIView.as_view(), name='client-notification-delete'),

    path('marketers/notifications/', MarketerNotificationListAPI.as_view(), name='marketer-notifications-list'),
    path('marketers/notifications/unread-count/', MarketerUnreadCountAPI.as_view(), name='marketer-notifications-unread-count'),
    path('marketers/notifications/<int:pk>/', MarketerNotificationDetailAPI.as_view(), name='marketer-notifications-detail'),
    path('marketers/notifications/<int:pk>/mark-read/', MarketerMarkReadAPI.as_view(), name='marketer-notifications-mark-read'),
    path('marketers/notifications/<int:pk>/mark-unread/', MarketerMarkUnreadAPI.as_view(), name='marketer-notifications-mark-unread'),
    path('marketers/notifications/mark-all-read/', MarketerMarkAllReadAPI.as_view(), name='marketer-notifications-mark-all-read'),

    path('marketers/chat/', MarketerChatListAPIView.as_view(), name='marketer-chat-list'),
    path('marketers/chat/<int:pk>/', MarketerChatDetailAPIView.as_view(), name='marketer-chat-detail'),
    path('marketers/chat/send/', MarketerChatSendAPIView.as_view(), name='marketer-chat-send'),
    path('marketers/chat/<int:pk>/delete/', MarketerChatDeleteAPIView.as_view(), name='marketer-chat-delete'),
    path('marketers/chat/delete-for-everyone/', MarketerChatDeleteForEveryoneAPIView.as_view(), name='marketer-chat-delete-for-everyone'),
    path('marketers/chat/unread-count/', MarketerChatUnreadCountAPIView.as_view(), name='marketer-chat-unread-count'),
    path('marketers/chat/mark-read/', MarketerChatMarkAsReadAPIView.as_view(), name='marketer-chat-mark-read'),
    path('marketers/chat/poll/', MarketerChatPollAPIView.as_view(), name='marketer-chat-poll'),

    # CLIENT CHAT / MESSAGING
    path('client/chat/', ClientChatListAPIView.as_view(), name='client-chat-list'),
    path('client/chat/<int:pk>/', ClientChatDetailAPIView.as_view(), name='client-chat-detail'),
    path('client/chat/send/', ClientChatSendAPIView.as_view(), name='client-chat-send'),
    path('client/chat/<int:pk>/delete/', ClientChatDeleteAPIView.as_view(), name='client-chat-delete'),
    path('client/chat/delete-for-everyone/', ClientChatDeleteForEveryoneAPIView.as_view(), name='client-chat-delete-for-everyone'),
    path('client/chat/unread-count/', ClientChatUnreadCountAPIView.as_view(), name='client-chat-unread-count'),
    path('client/chat/mark-read/', ClientChatMarkAsReadAPIView.as_view(), name='client-chat-mark-read'),
    path('client/chat/poll/', ClientChatPollAPIView.as_view(), name='client-chat-poll'),

    # Device tokens
    path('device-tokens/', DeviceTokenListView.as_view(), name='device-token-list'),
    path('device-tokens/register/', DeviceTokenRegisterView.as_view(), name='device-token-register'),


    # MARKETERS SIDE
    # marketer profile
    path('marketers/profile/', MarketerProfileView.as_view(), name='marketer-profile'),
    path('marketers/profile/update/', MarketerProfileUpdateView.as_view(), name='marketer-profile-update'),
    path('marketers/change-password/', MarketerChangePasswordView.as_view(), name='marketer-change-password'),
    path('marketers/transactions/', MarketerTransactionsView.as_view(), name='marketer-transactions'),
    
    # marketer dashboard
    path('marketers/dashboard/', MarketerDashboardAPIView.as_view(), name='marketer-dashboard'),
    path('marketers/dashboard/data/', MarketerChartRangeAPIView.as_view(), name='marketer-dashboard-data'),

    # marketer clients records
    path('marketers/clients/', MarketerClientListAPIView.as_view(), name='marketer-client-list'),
    path('marketers/clients/<int:pk>/', MarketerClientDetailAPIView.as_view(), name='marketer-client-detail'),

    # client View Estate Plot Details 
    path('clients/estates/', EstateListAPIView.as_view(), name='client-estate-list'),
    path('clients/estates/<int:pk>/', ClientEstateDetailAPIView.as_view(), name='client-estate-detail'),
    
    # Secure media endpoints for client estates
    path('clients/estates/<int:estate_id>/prototype-image/', SecurePrototypeImageAPIView.as_view(), name='client-estate-prototype-image'),
    path('clients/estates/<int:estate_id>/layout-image/', SecureEstateLayoutAPIView.as_view(), name='client-estate-layout-image'),
    path('clients/estates/<int:estate_id>/floor-plan/<int:plan_id>/', SecureFloorPlanAPIView.as_view(), name='client-estate-floor-plan'),
    path('clients/estates/<int:estate_id>/access-check/', ClientEstateAccessCheckAPIView.as_view(), name='client-estate-access-check'),



]
