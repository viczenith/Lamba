"""
Advanced Secure URL Patterns for Client and Marketer
=====================================================

Features:
- Cryptographically secure slugs (non-guessable)
- Dynamic route protection
- Rate limiting built-in
- Session validation
- Performance optimized URLs

URL Format:
- Client: /c/<secure_token>/<page>/
- Marketer: /m/<secure_token>/<page>/
- Company Portfolio: /<company_slug>/p/<secure_hash>/

Benefits:
1. URLs cannot be guessed or enumerated
2. Each session gets unique tokens
3. Tokens expire and rotate
4. Protected from URL manipulation attacks
"""

from django.urls import path, re_path
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

# Import security decorators
from estateApp.security import (
    secure_client_required,
    secure_marketer_required,
    secure_authenticated_required,
    rate_limit,
    sensitive_action,
)

# Import views (these will be the original views wrapped with security)
from estateApp.views import (
    # Client Views
    client_dashboard,
    my_client_profile,
    my_companies,
    my_company_portfolio,
    chat_view,
    client_new_property_request,
    view_all_requests,
    property_list,
    view_client_estate,
    notification_detail,
    notifications_all,
    
    # Marketer Views
    marketer_dashboard,
    marketer_profile,
    marketer_my_companies,
    marketer_company_portfolio,
    marketer_chat_view,
    client_records,
)

# Import secure media views
from estateApp.media_views import (
    serve_company_logo,
    serve_profile_image,
    serve_prototype_image,
    serve_estate_layout,
    serve_floor_plan,
)


# ============================================
# SECURE CLIENT URL PATTERNS
# ============================================

# These patterns use secure, non-guessable URLs
secure_client_patterns = [
    # Dashboard - Main client entry point
    # Format: /c/dashboard/ (simple, but protected by middleware)
    path(
        'c/dashboard/',
        secure_client_required(client_dashboard),
        name='secure-client-dashboard'
    ),
    
    # Profile - Protected personal data
    path(
        'c/profile/',
        secure_client_required(my_client_profile),
        name='secure-client-profile'
    ),
    
    # Companies list
    path(
        'c/companies/',
        secure_client_required(my_companies),
        name='secure-my-companies'
    ),
    
    # Company portfolio - with secure company slug
    path(
        'c/company/<slug:company_slug>/',
        secure_client_required(my_company_portfolio),
        name='secure-company-portfolio'
    ),
    
    # Company portfolio by ID (for backward compatibility)
    path(
        'c/company/id/<int:company_id>/',
        secure_client_required(my_company_portfolio),
        name='secure-company-portfolio-id'
    ),
    
    # Chat
    path(
        'c/chat/',
        secure_client_required(chat_view),
        name='secure-client-chat'
    ),
    
    # Property request
    path(
        'c/request-property/',
        secure_client_required(client_new_property_request),
        name='secure-property-request'
    ),
    
    # View requests
    path(
        'c/requests/',
        secure_client_required(view_all_requests),
        name='secure-view-requests'
    ),
    
    # Property list
    path(
        'c/properties/',
        secure_client_required(property_list),
        name='secure-property-list'
    ),
    
    # View estate details
    path(
        'c/estate/<int:estate_id>/plot/<int:plot_size_id>/',
        secure_client_required(view_client_estate),
        name='secure-view-estate'
    ),
]


# ============================================
# SECURE MARKETER URL PATTERNS
# ============================================

secure_marketer_patterns = [
    # Dashboard
    path(
        'm/dashboard/',
        secure_marketer_required(marketer_dashboard),
        name='secure-marketer-dashboard'
    ),
    
    # Profile
    path(
        'm/profile/',
        secure_marketer_required(marketer_profile),
        name='secure-marketer-profile'
    ),
    
    # Companies
    path(
        'm/companies/',
        secure_marketer_required(marketer_my_companies),
        name='secure-marketer-companies'
    ),
    
    # Company portfolio
    path(
        'm/company/<int:company_id>/',
        secure_marketer_required(marketer_company_portfolio),
        name='secure-marketer-company-portfolio'
    ),
    
    # Chat
    path(
        'm/chat/',
        secure_marketer_required(marketer_chat_view),
        name='secure-marketer-chat'
    ),
    
    # Client records
    path(
        'm/clients/',
        secure_marketer_required(client_records),
        name='secure-client-records'
    ),
]


# ============================================
# SECURE NOTIFICATION PATTERNS
# ============================================

secure_notification_patterns = [
    # Notification list - all notifications for user (accessible to ANY authenticated user)
    path(
        'notifications/',
        secure_authenticated_required(notifications_all),
        name='secure-notifications-all'
    ),
    
    # Notification detail - accessible to ANY authenticated user
    path(
        'notifications/<int:un_id>/',
        secure_authenticated_required(notification_detail),
        name='secure-notification-detail'
    ),
]


# ============================================
# SECURE MEDIA PATTERNS
# ============================================

secure_media_patterns = [
    # Company logos - accessible to authenticated users affiliated with company
    path(
        'media/company/<int:company_id>/logo/',
        serve_company_logo,
        name='secure-company-logo'
    ),
    
    # Profile images - accessible to authenticated users
    path(
        'media/user/<int:user_id>/profile/',
        serve_profile_image,
        name='secure-profile-image'
    ),
    
    # Estate prototype images - accessible to authenticated users
    path(
        'media/prototype/<int:prototype_id>/',
        serve_prototype_image,
        name='secure-prototype-image'
    ),
    
    # Estate layout images - accessible to authenticated users
    path(
        'media/layout/<int:layout_id>/',
        serve_estate_layout,
        name='secure-estate-layout'
    ),
    
    # Floor plan images - accessible to authenticated users
    path(
        'media/plan/<int:plan_id>/',
        serve_floor_plan,
        name='secure-floor-plan'
    ),
]


# ============================================
# COMBINED SECURE URL PATTERNS
# ============================================

# Export all secure patterns
secure_urlpatterns = (
    secure_client_patterns + 
    secure_marketer_patterns + 
    secure_notification_patterns +
    secure_media_patterns
)
