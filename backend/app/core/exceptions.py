from __future__ import annotations

from fastapi import HTTPException, status


class TurfmappException(Exception):
    """Base exception class for Turfmapp"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(TurfmappException):
    """Authentication related errors"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(TurfmappException):
    """Authorization related errors"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class NotFoundError(TurfmappException):
    """Resource not found errors"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ValidationError(TurfmappException):
    """Validation related errors"""
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY)


class ConflictError(TurfmappException):
    """Conflict errors (e.g., duplicate resources)"""
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status.HTTP_409_CONFLICT)


class GoogleOAuthError(TurfmappException):
    """Google OAuth related errors"""
    def __init__(self, message: str = "Google OAuth error"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class GoogleAPIError(TurfmappException):
    """Google API related errors"""
    def __init__(self, message: str, service: str = "Google API"):
        self.service = service
        super().__init__(f"{service}: {message}", status.HTTP_500_INTERNAL_SERVER_ERROR)


class TokenExpiredError(GoogleOAuthError):
    """Token expired error"""
    def __init__(self, account_email: str):
        self.account_email = account_email
        super().__init__(f"Access token expired for account {account_email}")


class AccountNotFoundError(NotFoundError):
    """Google account not found error"""
    def __init__(self, account_email: str):
        self.account_email = account_email
        super().__init__(f"Google account {account_email} not found")


class InsufficientScopesError(AuthorizationError):
    """Insufficient OAuth scopes error"""
    def __init__(self, required_scopes: list, granted_scopes: list = None):
        self.required_scopes = required_scopes
        self.granted_scopes = granted_scopes or []
        super().__init__(f"Insufficient OAuth scopes. Required: {required_scopes}")


def handle_google_api_error(error: Exception, service: str, operation: str) -> HTTPException:
    """Convert Google API errors to standardized HTTP exceptions."""
    from googleapiclient.errors import HttpError

    if isinstance(error, HttpError):
        status_code = error.resp.status

        if status_code == 401:
            return HTTPException(
                status_code=401,
                detail={
                    "error_code": "GOOGLE_AUTH_FAILED",
                    "message": f"Google {service} authentication failed. Please reconnect your account.",
                    "service": service,
                    "operation": operation
                }
            )
        elif status_code == 403:
            return HTTPException(
                status_code=403,
                detail={
                    "error_code": "GOOGLE_PERMISSION_DENIED",
                    "message": f"Insufficient permissions for Google {service}. Please check your account permissions.",
                    "service": service,
                    "operation": operation
                }
            )
        elif status_code == 404:
            return HTTPException(
                status_code=404,
                detail={
                    "error_code": "GOOGLE_RESOURCE_NOT_FOUND",
                    "message": f"Requested resource not found in Google {service}.",
                    "service": service,
                    "operation": operation
                }
            )
        elif status_code == 429:
            return HTTPException(
                status_code=429,
                detail={
                    "error_code": "GOOGLE_RATE_LIMIT",
                    "message": f"Google {service} rate limit exceeded. Please try again later.",
                    "service": service,
                    "operation": operation
                }
            )
        else:
            return HTTPException(
                status_code=500,
                detail={
                    "error_code": "GOOGLE_API_ERROR",
                    "message": f"Google {service} API error occurred.",
                    "service": service,
                    "operation": operation,
                    "status_code": status_code
                }
            )
    else:
        return HTTPException(
            status_code=500,
            detail={
                "error_code": "GOOGLE_UNEXPECTED_ERROR",
                "message": f"Unexpected error in Google {service}: {str(error)}",
                "service": service,
                "operation": operation,
                "error_type": type(error).__name__
            }
        )


def turfmapp_exception_to_http_exception(exc: TurfmappException) -> HTTPException:
    """Convert TurfmappException to HTTPException"""
    return HTTPException(status_code=exc.status_code, detail=exc.message)