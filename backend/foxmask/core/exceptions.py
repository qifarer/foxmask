# 
# foxmask/core/exceptions.py
# Custom exception classes for Foxmask application
from fastapi import HTTPException, status
from typing import Optional, Dict, Any
from loguru import logger


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


class KnowledgeBaseException(Exception):
    """知识库基础异常类"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "KNOWLEDGE_BASE_ERROR",
        details: Optional[Dict[str, Any]] = None,
        log_level: str = "ERROR"
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.log_level = log_level
        super().__init__(self.message)
        
        # 记录日志
        self._log_exception()
    
    def _log_exception(self):
        """记录异常日志"""
        log_method = getattr(logger, self.log_level.lower())
        log_method(
            "ErrorCode: {} | Message: {} | Details: {}",
            self.error_code, self.message, self.details
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ValidationException(KnowledgeBaseException):
    """数据验证异常"""
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        super().__init__(message, "VALIDATION_ERROR", details, "WARNING")


class NotFoundException(KnowledgeBaseException):
    """资源未找到异常"""
    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} not found: {resource_id}"
        details = {"resource_type": resource_type, "resource_id": resource_id}
        super().__init__(message, "NOT_FOUND_ERROR", details, "WARNING")


class DuplicateException(KnowledgeBaseException):
    """重复资源异常"""
    def __init__(self, resource_type: str, identifier: str):
        message = f"{resource_type} already exists: {identifier}"
        details = {"resource_type": resource_type, "identifier": identifier}
        super().__init__(message, "DUPLICATE_ERROR", details, "WARNING")


class PermissionException(KnowledgeBaseException):
    """权限异常"""
    def __init__(self, action: str, resource: str, user_id: Optional[str] = None):
        message = f"Permission denied for {action} on {resource}"
        details = {"action": action, "resource": resource}
        if user_id:
            details["user_id"] = user_id
        super().__init__(message, "PERMISSION_ERROR", details, "WARNING")


class DatabaseException(KnowledgeBaseException):
    """数据库操作异常"""
    def __init__(self, operation: str, collection: str, error: str):
        message = f"Database operation failed: {operation} on {collection}"
        details = {"operation": operation, "collection": collection, "error": error}
        super().__init__(message, "DATABASE_ERROR", details, "ERROR")


class ServiceException(Exception):
    def __init__(self, operation: str = "", error: str = ""):
        super().__init__(f"{operation}: {error}")
        self.operation = operation
        self.error = error


class ExternalServiceException(KnowledgeBaseException):
    """外部服务异常"""
    def __init__(self, service_name: str, operation: str, status_code: int, error: str):
        message = f"External service error: {service_name}.{operation}"
        details = {
            "service": service_name, 
            "operation": operation, 
            "status_code": status_code,
            "error": error
        }
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details, "ERROR")       