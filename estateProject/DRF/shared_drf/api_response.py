"""
Unified API Response Handler
============================
Provides consistent response formatting across all DRF endpoints.
Ensures all endpoints follow the same response structure.

Response Format:
- Success: {"success": true, "status_code": 200, "data": {...}, "message": "..."}
- Error: {"success": false, "status_code": 400, "errors": {...}, "message": "..."}
"""

from rest_framework.response import Response
from rest_framework import status as http_status
from typing import Any, Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class APIResponse:
    """Unified API response builder"""

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Operation successful",
        status_code: int = http_status.HTTP_200_OK,
        meta: Optional[Dict] = None,
    ) -> Response:
        """
        Return a success response with consistent format.

        Args:
            data: Response data (will be wrapped if not a dict)
            message: Human-readable success message
            status_code: HTTP status code
            meta: Optional metadata (pagination, counts, etc.)

        Returns:
            DRF Response object
        """
        response_data = {
            "success": True,
            "status_code": status_code,
            "message": message,
        }

        if data is not None:
            response_data["data"] = data

        if meta:
            response_data["meta"] = meta

        return Response(response_data, status=status_code)

    @staticmethod
    def error(
        message: str = "An error occurred",
        errors: Optional[Dict | List] = None,
        status_code: int = http_status.HTTP_400_BAD_REQUEST,
        error_code: Optional[str] = None,
    ) -> Response:
        """
        Return an error response with consistent format.

        Args:
            message: Human-readable error message
            errors: Field-level errors or error details
            status_code: HTTP status code
            error_code: Machine-readable error code

        Returns:
            DRF Response object
        """
        response_data = {
            "success": False,
            "status_code": status_code,
            "message": message,
        }

        if error_code:
            response_data["error_code"] = error_code

        if errors:
            response_data["errors"] = errors

        return Response(response_data, status=status_code)

    @staticmethod
    def created(
        data: Any = None,
        message: str = "Created successfully",
    ) -> Response:
        """Success response for resource creation (201)"""
        return APIResponse.success(
            data=data,
            message=message,
            status_code=http_status.HTTP_201_CREATED,
        )

    @staticmethod
    def no_content(message: str = "Success") -> Response:
        """Success response with no content (204)"""
        return Response(status=http_status.HTTP_204_NO_CONTENT)

    @staticmethod
    def bad_request(message: str, errors: Optional[Dict] = None) -> Response:
        """400 Bad Request error"""
        return APIResponse.error(
            message=message,
            errors=errors,
            status_code=http_status.HTTP_400_BAD_REQUEST,
        )

    @staticmethod
    def unauthorized(message: str = "Authentication required") -> Response:
        """401 Unauthorized error"""
        return APIResponse.error(
            message=message,
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
        )

    @staticmethod
    def forbidden(message: str = "Permission denied") -> Response:
        """403 Forbidden error"""
        return APIResponse.error(
            message=message,
            status_code=http_status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
        )

    @staticmethod
    def not_found(message: str = "Resource not found", error_code: Optional[str] = None) -> Response:
        """404 Not Found error"""
        return APIResponse.error(
            message=message,
            status_code=http_status.HTTP_404_NOT_FOUND,
            error_code=error_code or "NOT_FOUND",
        )

    @staticmethod
    def conflict(message: str, errors: Optional[Dict] = None) -> Response:
        """409 Conflict error (e.g., duplicate resource)"""
        return APIResponse.error(
            message=message,
            errors=errors,
            status_code=http_status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
        )

    @staticmethod
    def validation_error(errors: Dict) -> Response:
        """422 Unprocessable Entity (validation error)"""
        return APIResponse.error(
            message="Validation failed",
            errors=errors,
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
        )

    @staticmethod
    def server_error(message: str = "Internal server error", error_code: Optional[str] = None) -> Response:
        """500 Internal Server Error"""
        logger.error(f"Internal server error: {message}")
        return APIResponse.error(
            message=message,
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=error_code or "SERVER_ERROR",
        )

    @staticmethod
    def paginated_response(
        data: Any,
        page_number: int = 1,
        page_size: int = 20,
        total_count: int = 0,
        total_pages: int = 1,
        message: str = "Data retrieved successfully",
    ) -> Response:
        """Response with pagination metadata"""
        return APIResponse.success(
            data=data,
            message=message,
            meta={
                "pagination": {
                    "current_page": page_number,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                }
            },
        )
