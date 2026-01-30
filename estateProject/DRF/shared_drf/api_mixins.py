"""
Unified API Mixins
==================
Reusable mixins for consistent API behavior across all views.

Provides:
- Company scoping (multi-tenant isolation)
- Audit logging
- Error handling
- Pagination standardization
- Response formatting
"""

from rest_framework import status, serializers
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import QuerySet, Model
import logging

from .api_response import APIResponse

logger = logging.getLogger(__name__)


class CompanyMixin:
    """
    Ensures multi-tenant data isolation by filtering queryset by company.
    Automatically scopes all queries to the authenticated user's company.
    """

    def get_company(self):
        """Extract company from authenticated user"""
        user = self.request.user
        if not user or not user.is_authenticated:
            return None
        return getattr(user, "company_profile", None) or getattr(user, "company", None)

    def get_queryset(self):
        """Override to ensure company scoping"""
        queryset = super().get_queryset()
        company = self.get_company()

        if not company:
            return queryset.none()

        # Filter by company_id or company field
        if hasattr(queryset.model, "company"):
            queryset = queryset.filter(company=company)
        elif hasattr(queryset.model, "company_id"):
            queryset = queryset.filter(company_id=company.id)

        return queryset


class AuditLogMixin:
    """
    Logs all API access and modifications for security/compliance.
    """

    def dispatch(self, request, *args, **kwargs):
        """Log the request"""
        logger.info(
            f"API Request: {request.method} {request.path}",
            extra={
                "user": str(request.user),
                "company": str(getattr(request.user, "company_profile", None)),
                "ip": self._get_client_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT"),
            },
        )
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0]
        return request.META.get("REMOTE_ADDR")

    def log_action(self, action: str, instance: Model, details: dict = None):
        """Log a specific action"""
        logger.info(
            f"API Action: {action} - {instance.__class__.__name__}",
            extra={
                "user": str(self.request.user),
                "instance_id": instance.id,
                "company": str(getattr(self.request.user, "company_profile", None)),
                "details": details or {},
            },
        )


class CRUDResponseMixin:
    """
    Provides consistent response formats for CRUD operations.
    Automatically handles success/error responses.
    """

    def get_response_message(self, action: str) -> str:
        """Get default message for action"""
        messages = {
            "create": "Resource created successfully",
            "retrieve": "Resource retrieved successfully",
            "update": "Resource updated successfully",
            "partial_update": "Resource updated successfully",
            "delete": "Resource deleted successfully",
            "list": "Resources retrieved successfully",
        }
        return messages.get(action, "Operation completed successfully")

    def success_response(
        self,
        data=None,
        action: str = None,
        status_code: int = status.HTTP_200_OK,
        message: str = None,
    ) -> Response:
        """Return standardized success response"""
        if message is None and action:
            message = self.get_response_message(action)

        return APIResponse.success(
            data=data,
            message=message or "Success",
            status_code=status_code,
        )

    def error_response(
        self,
        message: str,
        errors: dict = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> Response:
        """Return standardized error response"""
        return APIResponse.error(
            message=message,
            errors=errors,
            status_code=status_code,
        )


class ValidationMixin:
    """
    Provides common validation patterns and error responses.
    """

    def validate_and_save(self, serializer: serializers.Serializer):
        """
        Validate and save serializer, returning appropriate response.

        Returns:
            (is_valid, response) tuple
        """
        if not serializer.is_valid():
            return False, APIResponse.validation_error(serializer.errors)

        try:
            instance = serializer.save()
            return True, instance
        except Exception as e:
            logger.error(f"Save error: {str(e)}", exc_info=True)
            return False, APIResponse.server_error(str(e))

    def get_object_or_error(self, queryset: QuerySet, **kwargs):
        """
        Get single object or return 404 response.

        Returns:
            (instance, response) tuple where response is None if found
        """
        try:
            instance = get_object_or_404(queryset, **kwargs)
            return instance, None
        except Exception as e:
            return None, APIResponse.not_found(str(e))


class PaginationMixin:
    """
    Provides consistent pagination across list endpoints.
    """

    page_size = 20
    max_page_size = 100

    def paginate_queryset(self, queryset: QuerySet):
        """
        Paginate queryset and return (data, pagination_meta).
        """
        page_size = self.request.query_params.get("page_size", self.page_size)
        try:
            page_size = min(int(page_size), self.max_page_size)
        except (ValueError, TypeError):
            page_size = self.page_size

        page_number = self.request.query_params.get("page", 1)
        try:
            page_number = int(page_number)
        except (ValueError, TypeError):
            page_number = 1

        total_count = queryset.count()
        total_pages = (total_count + page_size - 1) // page_size

        start = (page_number - 1) * page_size
        end = start + page_size

        paginated_data = list(queryset[start:end])

        meta = {
            "pagination": {
                "current_page": page_number,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
            }
        }

        return paginated_data, meta

    def paginated_response(
        self,
        data,
        message: str = "Data retrieved successfully",
        status_code: int = status.HTTP_200_OK,
    ) -> Response:
        """Return paginated response with metadata"""
        # Extract pagination meta if included
        meta = None
        if isinstance(data, dict) and "meta" in data:
            meta = data.pop("meta")

        return APIResponse.success(
            data=data,
            message=message,
            status_code=status_code,
            meta=meta,
        )
