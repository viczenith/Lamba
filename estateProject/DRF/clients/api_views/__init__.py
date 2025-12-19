"""
Client API Views Module
========================
Exports all client-related DRF API views.
"""

from .client_estate_detail_views import (
    # Main views
    ClientEstateDetailAPIView,
    ClientEstateAccessCheckAPIView,
    
    # Secure media views
    SecurePrototypeImageAPIView,
    SecureEstateLayoutAPIView,
    SecureFloorPlanAPIView,
    
    # Base classes (for extension if needed)
    SecureClientBaseView,
    SecureMediaBaseView,
    
    # Throttle classes
    ClientEstateDetailThrottle,
    SecureMediaThrottle,
    BurstThrottle,
)

from .client_dashboard_views import (
    # Dashboard views
    ClientDashboardAPIView,
    PriceUpdateDetailAPIView,
    EstateListAPIView,
    ActivePromotionsListAPIView,
    PromotionsListAPIView,
    PromotionDetailAPIView,
    
    # Throttle classes
    ClientDashboardThrottle,
    ClientDashboardBurstThrottle,
    PromotionDetailThrottle,
    
    # Utility functions
    get_user_affiliated_companies,
    log_access,
    validate_integer_param,
    sanitize_string,
)

from .device_token_views import (
    # Device token views
    DeviceTokenRegisterView,
    DeviceTokenListView,
    
    # Throttle classes
    DeviceTokenRegisterThrottle,
    DeviceTokenListThrottle,
)

__all__ = [
    # Estate Detail views
    'ClientEstateDetailAPIView',
    'ClientEstateAccessCheckAPIView',
    
    # Secure media views
    'SecurePrototypeImageAPIView',
    'SecureEstateLayoutAPIView',
    'SecureFloorPlanAPIView',
    
    # Base classes
    'SecureClientBaseView',
    'SecureMediaBaseView',
    
    # Estate Detail Throttle classes
    'ClientEstateDetailThrottle',
    'SecureMediaThrottle',
    'BurstThrottle',
    
    # Dashboard views
    'ClientDashboardAPIView',
    'PriceUpdateDetailAPIView',
    'EstateListAPIView',
    'ActivePromotionsListAPIView',
    'PromotionsListAPIView',
    'PromotionDetailAPIView',
    
    # Dashboard Throttle classes
    'ClientDashboardThrottle',
    'ClientDashboardBurstThrottle',
    'PromotionDetailThrottle',
    
    # Dashboard Utility functions
    'get_user_affiliated_companies',
    'log_access',
    'validate_integer_param',
    'sanitize_string',
    
    # Device Token views
    'DeviceTokenRegisterView',
    'DeviceTokenListView',
    
    # Device Token Throttle classes
    'DeviceTokenRegisterThrottle',
    'DeviceTokenListThrottle',
]
