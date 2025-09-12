# 
# foxmask/core/exceptions.py
# Custom exception classes for Foxmask application
from fastapi import HTTPException, status
from typing import Optional, Dict, Any, List
import json

class FoxmaskException(HTTPException):
    """Base exception for Foxmask application"""
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        detail: str,
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response"""
        return {
            "error_code": self.error_code,
            "detail": self.detail,
            "context": self.context
        }

class ValidationError(FoxmaskException):
    """Validation related errors"""
    
    def __init__(
        self,
        detail: str = "Validation failed",
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            detail=detail,
            context=context,
            headers=headers
        )

class AuthenticationError(FoxmaskException):
    """Authentication related errors"""
    
    def __init__(
        self,
        detail: str = "Authentication failed",
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
            detail=detail,
            context=context,
            headers=headers
        )

class AuthorizationError(FoxmaskException):
    """Authorization related errors"""
    
    def __init__(
        self,
        detail: str = "Authorization failed",
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
            detail=detail,
            context=context,
            headers=headers
        )

class NotFoundError(FoxmaskException):
    """Resource not found errors"""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        if detail is None:
            detail = f"{resource_type} with ID {resource_id} not found"
        
        context = context or {}
        context.update({
            "resource_type": resource_type,
            "resource_id": resource_id
        })
        
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND_ERROR",
            detail=detail,
            context=context,
            headers=headers
        )

class DatabaseError(FoxmaskException):
    """Database operation errors"""
    
    def __init__(
        self,
        operation: str,
        detail: str = "Database operation failed",
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        context = context or {}
        context.update({"operation": operation})
        
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            detail=detail,
            context=context,
            headers=headers
        )

class ExternalServiceError(FoxmaskException):
    """External service errors"""
    
    def __init__(
        self,
        service_name: str,
        operation: str,
        detail: str = "External service operation failed",
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        context = context or {}
        context.update({
            "service_name": service_name,
            "operation": operation
        })
        
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="EXTERNAL_SERVICE_ERROR",
            detail=detail,
            context=context,
            headers=headers
        )

class RateLimitError(FoxmaskException):
    """Rate limiting errors"""
    
    def __init__(
        self,
        limit: int,
        window: str,
        detail: str = "Rate limit exceeded",
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        context = context or {}
        context.update({
            "limit": limit,
            "window": window
        })
        
        if headers is None:
            headers = {}
        
        # Add rate limit headers
        headers.update({
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "60"  # Example: reset in 60 seconds
        })
        
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_ERROR",
            detail=detail,
            context=context,
            headers=headers
        )

class BusinessLogicError(FoxmaskException):
    """Business logic violation errors"""
    
    def __init__(
        self,
        rule: str,
        detail: str = "Business rule violation",
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        context = context or {}
        context.update({"rule": rule})
        
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="BUSINESS_LOGIC_ERROR",
            detail=detail,
            context=context,
            headers=headers
        )

class FileProcessingError(FoxmaskException):
    """File processing errors"""
    
    def __init__(
        self,
        operation: str,
        detail: str = "File processing failed",
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        context = context or {}
        context.update({"operation": operation})
        
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="FILE_PROCESSING_ERROR",
            detail=detail,
            context=context,
            headers=headers
        )

class KafkaError(FoxmaskException):
    """Kafka messaging errors"""
    
    def __init__(
        self,
        operation: str,
        topic: Optional[str] = None,
        detail: str = "Kafka operation failed",
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        context = context or {}
        context.update({
            "operation": operation,
            "topic": topic
        })
        
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="KAFKA_ERROR",
            detail=detail,
            context=context,
            headers=headers
        )

class RetryableError(FoxmaskException):
    """Errors that can be retried"""
    
    def __init__(
        self,
        operation: str,
        max_retries: int = 3,
        detail: str = "Operation failed but can be retried",
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        context = context or {}
        context.update({
            "operation": operation,
            "max_retries": max_retries,
            "retryable": True
        })
        
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="RETRYABLE_ERROR",
            detail=detail,
            context=context,
            headers=headers
        )