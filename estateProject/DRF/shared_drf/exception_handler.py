"""
Unified API Exception Handler
==============================
Handles all exceptions consistently across DRF endpoints.

All exceptions are caught and returned in standardized format:
{"success": false, "status_code": ..., "message": "...", "errors": {...}}
"""

from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework import status
from rest_framework.response import Response
from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist
from django.http import Http404
import logging

from .api_response import APIResponse

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent response format.
    
    Handles:
    - DRF ValidationError, PermissionDenied, Http404, NotAuthenticated
    - Django ValidationError, PermissionDenied, ObjectDoesNotExist, Http404
    - Custom API exceptions
    """

    # Log the exception
    view = context.get("view")
    request = context.get("request")
    logger.error(
        f"API Exception: {exc.__class__.__name__}",
        extra={
            "exception": str(exc),
            "view": view.__class__.__name__ if view else None,
            "method": request.method if request else None,
            "path": request.path if request else None,
            "user": str(request.user) if request else None,
        },
        exc_info=True,
    )

    # Handle DRF exceptions first
    response = drf_exception_handler(exc, context)

    if response is not None:
        # Reformat DRF exception response
        return _format_response(response, exc)

    # Handle Django exceptions
    if isinstance(exc, PermissionDenied):
        return APIResponse.forbidden(str(exc) or "Permission denied")

    if isinstance(exc, Http404):
        return APIResponse.not_found(str(exc) or "Not found")

    if isinstance(exc, ObjectDoesNotExist):
        return APIResponse.not_found(f"{exc.__class__.__name__} not found")

    if isinstance(exc, ValidationError):
        errors = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
        return APIResponse.validation_error(errors)

    # Handle unhandled exceptions
    logger.critical(
        f"Unhandled exception: {exc.__class__.__name__}",
        exc_info=True,
        extra={"view": context.get("view").__class__.__name__},
    )

    return APIResponse.server_error("An unexpected error occurred")


def _format_response(response: Response, exc) -> Response:
    """
    Reformat DRF exception response to match our standard format.
    """
    status_code = response.status_code
    exc_class = exc.__class__.__name__

    # Extract data from DRF response
    data = response.data if response.data else {}

    # Determine message
    if isinstance(data, dict):
        message = data.get("detail", str(exc))
    elif isinstance(data, list):
        message = " ".join(str(item) for item in data)
    else:
        message = str(data) or str(exc)

    # Clean up error details
    errors = None
    if isinstance(data, dict) and "detail" in data:
        errors = {k: v for k, v in data.items() if k != "detail"}
        if not errors:
            errors = None

    return APIResponse.error(
        message=message,
        errors=errors,
        status_code=status_code,
        error_code=_get_error_code(exc_class, status_code),
    )


def _get_error_code(exc_class: str, status_code: int) -> str:
    """Map exception class to error code"""
    error_map = {
        "NotAuthenticated": "UNAUTHORIZED",
        "AuthenticationFailed": "UNAUTHORIZED",
        "PermissionDenied": "FORBIDDEN",
        "NotFound": "NOT_FOUND",
        "ValidationError": "VALIDATION_ERROR",
        "ParseError": "INVALID_REQUEST",
        "MethodNotAllowed": "METHOD_NOT_ALLOWED",
        "NotAcceptable": "NOT_ACCEPTABLE",
        "Throttled": "RATE_LIMITED",
        "ObjectDoesNotExist": "NOT_FOUND",
        "Http404": "NOT_FOUND",
    }

    return error_map.get(exc_class, f"ERROR_{status_code}")
