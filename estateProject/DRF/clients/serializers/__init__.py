"""
Client Serializers Module
==========================
Exports all client-related DRF serializers.
"""

from .client_estate_detail_serializer import (
    # Main serializers
    ClientEstateDetailSerializer,
    ClientEstateDetailResponseSerializer,
    ErrorResponseSerializer,
    
    # Nested serializers
    CompanyMinimalSerializer as EstateCompanyMinimalSerializer,
    PlotSizeSerializer,
    ProgressStatusSerializer,
    AmenityItemSerializer,
    EstateAmenityWrapperSerializer,
    PrototypeSerializer,
    EstateLayoutSerializer,
    FloorPlanSerializer,
    EstateMapSerializer,
)

from .client_dashboard_serializers import (
    # Dashboard serializers
    EstateDetailSerializer,
    PromotionDashboardSerializer,
    PriceHistoryListSerializer,
    PromotionDetailSerializer,
    PromotionListItemSerializer,
    PromotionalOfferSimpleSerializer,
    EstateSizePriceSerializer,
    CompanyDashboardSerializer,
    DashboardStatsSerializer,
    UserInfoSerializer,
    ClientDashboardResponseSerializer,
    
    # Utility functions
    sanitize_string,
    safe_float,
    safe_decimal_to_float,
    calculate_discount_price,
)

from .device_token_serializers import (
    # Device token serializers
    DeviceTokenSerializer,
    DeviceTokenListSerializer,
    
    # Constants
    MAX_TOKEN_LENGTH,
    MAX_APP_VERSION_LENGTH,
    MAX_DEVICE_MODEL_LENGTH,
    VALID_PLATFORMS,
)

from .permissions import (
    # Permission classes
    IsRecipient,
    IsClientUser,
    IsCompanyMember,
    IsAuthenticatedClient,
)

__all__ = [
    # Estate Detail serializers
    'ClientEstateDetailSerializer',
    'ClientEstateDetailResponseSerializer',
    'ErrorResponseSerializer',
    
    # Estate Detail nested serializers
    'EstateCompanyMinimalSerializer',
    'PlotSizeSerializer',
    'ProgressStatusSerializer',
    'AmenityItemSerializer',
    'EstateAmenityWrapperSerializer',
    'PrototypeSerializer',
    'EstateLayoutSerializer',
    'FloorPlanSerializer',
    'EstateMapSerializer',
    
    # Dashboard serializers
    'EstateDetailSerializer',
    'PromotionDashboardSerializer',
    'PriceHistoryListSerializer',
    'PromotionDetailSerializer',
    'PromotionListItemSerializer',
    'PromotionalOfferSimpleSerializer',
    'EstateSizePriceSerializer',
    'CompanyDashboardSerializer',
    'DashboardStatsSerializer',
    'UserInfoSerializer',
    'ClientDashboardResponseSerializer',
    
    # Dashboard Utility functions
    'sanitize_string',
    'safe_float',
    'safe_decimal_to_float',
    'calculate_discount_price',
    
    # Device Token serializers
    'DeviceTokenSerializer',
    'DeviceTokenListSerializer',
    
    # Device Token constants
    'MAX_TOKEN_LENGTH',
    'MAX_APP_VERSION_LENGTH',
    'MAX_DEVICE_MODEL_LENGTH',
    'VALID_PLATFORMS',
    
    # Permission classes
    'IsRecipient',
    'IsClientUser',
    'IsCompanyMember',
    'IsAuthenticatedClient',
]
