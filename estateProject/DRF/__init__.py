"""
Django REST Framework (DRF) API Layer
======================================

Unified API implementation with consistent response formats, authentication,
multi-tenant isolation, and comprehensive error handling.

Key Modules:
- shared_drf.api_response: Unified response formatter
- shared_drf.exception_handler: Global exception handler
- shared_drf.api_mixins: Reusable view mixins
- shared_drf.pagination: Standard pagination
- shared_drf.auth_views: Authentication endpoints

Usage:
    from DRF.shared_drf.api_response import APIResponse
    from DRF.shared_drf.api_mixins import CompanyMixin, AuditLogMixin
    
    class MyView(CompanyMixin, AuditLogMixin, APIView):
        def get(self, request):
            return APIResponse.success(data={...})
"""

default_app_config = 'DRF.apps.DrfConfig'
