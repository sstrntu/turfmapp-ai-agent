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


def turfmapp_exception_to_http_exception(exc: TurfmappException) -> HTTPException:
    """Convert TurfmappException to HTTPException"""
    return HTTPException(status_code=exc.status_code, detail=exc.message)